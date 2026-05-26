/* eslint-disable */
/* Auto-generated from Pydantic schemas in backend/schemas.py */

export interface HealthResponse {
    status?: string;
    postgres?: boolean;
    redis?: boolean;
    neo4j?: boolean;
    ac?: string;
}
export interface CandidateResponse {
    ac_id?: string;
    candidates?: Record<string, any>[];
}
export interface SchemeResponse {
    ac_id?: string;
    schemes?: Record<string, any>[];
}
export interface ConversionOverviewResponse {
    ac_id?: string;
    booths?: Record<string, any>[];
}
export interface BoothGeoResponse {
    ac_id?: string;
    count?: number;
    geo?: Record<string, any>[];
}
export interface IntelSummaryResponse {
    ac_id?: string;
    postgres_status?: string;
    neo4j_status?: string;
    total_booths?: number;
    total_voters?: number;
    booth_details?: Record<string, any>[];
}
