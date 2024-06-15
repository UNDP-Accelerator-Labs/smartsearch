/**
 * NLP-API provides useful Natural Language Processing capabilities as API.
 * Copyright (C) 2024 UNDP Accelerator Labs, Josua Krause
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
export type ApiUserResult = {
  name: string | undefined;
};

export type UserResult = {
  userName: string | undefined;
};

export type SearchFilters = { [key: string]: string[] };

export type ApiStatResult = {
  doc_count: number;
  fields: { [key: string]: { [key: string]: number } };
};

export type Stats = {
  count?: number;
  fields: { [key: string]: { [key: string]: number | undefined } };
};

export type ApiSearchResult = {
  hits: {
    base: string;
    doc_id: number;
    main_id: string;
    meta: {
      date: string;
      doc_type: string;
      iso3?: string[];
      language?: string[];
      status: string;
    };
    score: number;
    snippets: string[];
    url: string;
    title: string;
  }[];
  status: string;
};

export type SearchResult = {
  hits: {
    base: string;
    docId: number;
    mainId: string;
    meta: {
      date: string;
      docType: string;
      iso3?: string[];
      language?: string[];
      status: string;
    };
    score: number;
    snippets: string[];
    url: string;
    title: string;
  }[];
  status: string;
};

export type SearchState = {
  q: string;
  filter: string;
  p: number;
};

export type DeepDive = 'circular_economy';

export type Collection = {
  id: number;
  name: string;
};

type DeepDiveResult = {
  reason: string;
  cultural: number;
  economic: number;
  educational: number;
  institutional: number;
  legal: number;
  political: number;
  technological: number;
};

type ApiDocumentObj = {
  id: number;
  main_id: string;
  deep_dive: number;
  verify_key: string;
  deep_dive_key: string;
  is_valid: boolean | undefined;
  verify_reason: string | undefined;
  deep_dive_result: DeepDiveResult | undefined;
  error: string | undefined;
};

export type DocumentObj = {
  id: number;
  mainId: string;
  collectionId: number;
  verifyKey: string;
  deepDiveKey: string;
  isValid: boolean | undefined;
  verifyReason: string | undefined;
  deepDiveResult: DeepDiveResult | undefined;
  error: string | undefined;
};

export type ApiCollectionResponse = {
  collection_id: number;
};

export type CollectionResponse = {
  collectionId: number;
};

export type CollectionListResponse = {
  collections: Collection[];
};

export type ApiDocumentResponse = {
  document_ids: number[];
};

export type DocumentResponse = {
  documentIds: number[];
};

export type ApiDocumentListResponse = {
  documents: ApiDocumentObj[];
};

export type DocumentListResponse = {
  documents: DocumentObj[];
};

export type FulltextResponse = {
  content: string | undefined;
  error: string | undefined;
};
