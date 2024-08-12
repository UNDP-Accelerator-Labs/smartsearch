# NLP-API provides useful Natural Language Processing capabilities as API.
# Copyright (C) 2024 UNDP Accelerator Labs, Josua Krause
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import json
import os
import traceback
from typing import cast, Literal, TypedDict, TypeVar

import redis as redis_lib
from redipy import Redis, RedisConfig
from scattermind.api.api import ScattermindAPI
from scattermind.api.loader import load_api
from scattermind.system.base import TaskId
from scattermind.system.config.loader import ConfigJSON
from scattermind.system.names import GNamespace
from scattermind.system.torch_util import tensor_to_str

from app.misc.util import only
from app.system.config import Config


T = TypeVar('T')


PseudoRedisName = Literal["rmain", "rdata", "rcache", "rbody", "rworker"]


QueueStat = TypedDict('QueueStat', {
    "id": str,
    "name": str,
    "queue_length": int,
    "listeners": int,
})


NERResponse = TypedDict('NERResponse', {
    "ranges": list[tuple[int, int]],
    "text": list[str],
})


def get_redis(
        config_fname: str,
        *,
        redis_name: PseudoRedisName,
        overwrite_prefix: str | None) -> Redis:
    with open(config_fname, "rb") as fin:
        config_obj = cast(ConfigJSON, json.load(fin))
    if redis_name == "rmain":
        if config_obj["client_pool"]["name"] != "redis":
            raise ValueError(
                "client_pool is not redis: "
                f"{config_obj['client_pool']['name']}")
        cfg: RedisConfig = config_obj["client_pool"]["cfg"]
    elif redis_name == "rcache":
        if config_obj["graph_cache"]["name"] != "redis":
            raise ValueError(
                "graph_cache is not redis: "
                f"{config_obj['graph_cache']['name']}")
        cfg = config_obj["graph_cache"]["cfg"]
    elif redis_name == "rbody":
        if config_obj["data_store"]["name"] != "redis":
            raise ValueError(
                "data_store is not redis: "
                f"{config_obj['data_store']['name']}")
        cfg = config_obj["data_store"]["cfg"]
    elif redis_name == "rdata":
        if config_obj["queue_pool"]["name"] != "redis":
            raise ValueError(
                "queue_pool is not redis: "
                f"{config_obj['queue_pool']['name']}")
        cfg = config_obj["queue_pool"]["cfg"]
    elif redis_name == "rworker":
        if config_obj["executor_manager"]["name"] != "redis":
            raise ValueError(
                "executor_manager is not redis: "
                f"{config_obj['executor_manager']['name']}")
        cfg = config_obj["executor_manager"]["cfg"]
    else:
        raise ValueError(f"invalid redis_name: {redis_name}")
    if overwrite_prefix:
        old_prefix = cfg.get("prefix")
        if not old_prefix or old_prefix == overwrite_prefix:
            raise ValueError(
                f"cannot overwrite prefix {old_prefix} "
                f"with {overwrite_prefix}")
        cfg["prefix"] = overwrite_prefix
    return Redis(cfg=cfg)


def clear_redis(config_fname: str, redis_name: PseudoRedisName) -> None:
    redis = get_redis(
        config_fname, redis_name=redis_name, overwrite_prefix=None)
    redis.flushall()


def load_smind(config_fname: str) -> ScattermindAPI:
    with open(config_fname, "rb") as fin:
        config_obj = json.load(fin)
    return load_api(config_obj)


class GraphProfile:
    def __init__(self, smind: ScattermindAPI, ns: GNamespace) -> None:
        self._smind = smind
        self._ns = ns
        inputs = list(smind.main_inputs(ns))
        outputs = list(smind.main_outputs(ns))
        self._inputs = inputs
        self._outputs = outputs

        self._output_field: str | None = None
        self._output_size: int | None = None

    def get_api(self) -> ScattermindAPI:
        return self._smind

    def get_ns(self) -> GNamespace:
        return self._ns

    def get_input_fields(self) -> list[str]:
        return self._inputs

    def get_outputs(self) -> list[str]:
        return self._outputs

    def get_output_field(self) -> str:
        output_field = self._output_field
        if output_field is None:
            outputs = self._outputs
            if len(outputs) != 1:
                raise ValueError(f"invalid graph outputs: {outputs}")
            output_field = outputs[0]
            self._output_field = output_field
        return output_field

    def get_output_size(self) -> int:
        output_size = self._output_size
        if output_size is None:
            _, output_shape = self._smind.output_format(
                self._ns, self.get_output_field())
            if len(output_shape) != 1:
                raise ValueError(f"invalid graph output shape: {output_shape}")
            output_size = output_shape[0]
            if output_size is None:
                raise ValueError(f"graph {self._ns} has variable shape")
            self._output_size = output_size
        return output_size


def load_graph(
        config: Config,
        smind: ScattermindAPI,
        graph_fname: str) -> GraphProfile:
    with open(os.path.join(config["graphs"], graph_fname), "rb") as fin:
        graph_def_obj = json.load(fin)
    ns: GNamespace = smind.load_graph(graph_def_obj)
    return GraphProfile(smind, ns)


def get_queue_stats(smind: ScattermindAPI) -> list[QueueStat]:
    try:
        return [
            {
                "id": stat["id"].to_parseable(),
                "name": stat["name"].get(),
                "queue_length": stat["queue_length"],
                "listeners": stat["listeners"],
            }
            for stat in smind.get_queue_stats()
        ]
    except redis_lib.ConnectionError:
        print(traceback.format_exc())
        return []


def get_text_results_immediate(
        texts: list[str],
        *,
        graph_profile: GraphProfile,
        output_sample: T) -> list[T | None]:
    if not texts:
        return []
    smind = graph_profile.get_api()
    ns = graph_profile.get_ns()
    input_field = only(graph_profile.get_input_fields())
    output_field = graph_profile.get_output_field()
    lookup: dict[TaskId, int] = {}
    for ix, text in enumerate(texts):
        task_id = smind.enqueue_task(
            ns,
            {
                input_field: text,
            })
        print(f"enqueue task {task_id} ({len(text)})")
        lookup[task_id] = ix
    sent_tasks = list(lookup.keys())
    res: dict[int, T] = {}
    tids: list[TaskId] = []
    success = False
    try:
        for tid, resp in smind.wait_for(sent_tasks, timeout=300):
            if resp["error"] is not None:
                error = resp["error"]
                print(f"{error['code']} ({error['ctx']}): {error['message']}")
                print("\n".join(error["traceback"]))
            result = resp["result"]
            if result is not None:
                if output_field in ("text", "tags"):
                    output: T = cast(T, tensor_to_str(result[output_field]))
                else:
                    output = cast(T, list(result[output_field].cpu().tolist()))
                if not isinstance(output, type(output_sample)):
                    raise ValueError(
                        "output does not match sample. "
                        f"output={output} sample={output_sample} "
                        f"{type(output)}<:{type(output_sample)}")
                curix = lookup[tid]
                res[curix] = output
            print(
                f"retrieved task {tid} ({resp['ns']}) {resp['status']} "
                f"{resp['duration']}s retry={resp['retries']}")
            tids.append(tid)
        success = True
    finally:
        tasks = tids if success else sent_tasks
        for tid in tasks:
            smind.clear_task(tid)
    return [res.get(ix, None) for ix in range(len(texts))]


def get_ner_results_immediate(
        texts: list[str],
        *,
        graph_profile: GraphProfile) -> list[NERResponse | None]:
    if not texts:
        return []
    smind = graph_profile.get_api()
    ns = graph_profile.get_ns()
    input_field = only(graph_profile.get_input_fields())
    lookup: dict[TaskId, int] = {}
    for ix, text in enumerate(texts):
        task_id = smind.enqueue_task(
            ns,
            {
                input_field: text,
            })
        print(f"enqueue task {task_id} ({len(text)})")
        lookup[task_id] = ix
    sent_tasks = list(lookup.keys())

    res: dict[int, NERResponse] = {}
    tids: list[TaskId] = []
    success = False
    try:
        for tid, resp in smind.wait_for(sent_tasks, timeout=300):
            if resp["error"] is not None:
                error = resp["error"]
                print(f"{error['code']} ({error['ctx']}): {error['message']}")
                print("\n".join(error["traceback"]))
            result = resp["result"]
            if result is not None:
                ranges: list[tuple[int, int]] = [
                    tuple(cur_range)
                    for cur_range in result["ranges"].T.cpu().tolist()
                ]
                res_texts: list[str] = [
                    bytes(text).rstrip(b"\0").decode("utf-8")
                    for text in result["text"].cpu().tolist()
                ]
                if (len(ranges) == 1
                        and len(res_texts) == 1
                        and ranges[0] == (0, 0)
                        and not res_texts[0]):
                    ranges = []
                    res_texts = []
                curix = lookup[tid]
                res[curix] = {
                    "ranges": ranges,
                    "text": res_texts,
                }
            print(
                f"retrieved task {tid} ({resp['ns']}) {resp['status']} "
                f"{resp['duration']}s retry={resp['retries']}")
            tids.append(tid)
        success = True
    finally:
        tasks = tids if success else sent_tasks
        for tid in tasks:
            smind.clear_task(tid)
    return [res.get(ix, None) for ix in range(len(texts))]
