export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      sources: {
        Row: {
          id: number;
          name: string;
          api_base_url: string | null;
          is_active: boolean | null;
          last_synced_at: string | null;
          config: Json | null;
        };
        Insert: {
          id?: never;
          name: string;
          api_base_url?: string | null;
          is_active?: boolean | null;
          last_synced_at?: string | null;
          config?: Json | null;
        };
        Update: {
          id?: never;
          name?: string;
          api_base_url?: string | null;
          is_active?: boolean | null;
          last_synced_at?: string | null;
          config?: Json | null;
        };
      };
      companies: {
        Row: {
          id: number;
          name: string;
          normalized_name: string;
          website: string | null;
          industry: string | null;
          company_size: string | null;
          sic_code: string | null;
          metadata: Json | null;
          companies_house_number: string | null;
          sic_codes: string[] | null;
          company_status: string | null;
          date_of_creation: string | null;
          registered_address: Json | null;
          enriched_at: string | null;
        };
        Insert: {
          id?: never;
          name: string;
          normalized_name: string;
          website?: string | null;
          industry?: string | null;
          company_size?: string | null;
          sic_code?: string | null;
          metadata?: Json | null;
          companies_house_number?: string | null;
          sic_codes?: string[] | null;
          company_status?: string | null;
          date_of_creation?: string | null;
          registered_address?: Json | null;
          enriched_at?: string | null;
        };
        Update: {
          id?: never;
          name?: string;
          normalized_name?: string;
          website?: string | null;
          industry?: string | null;
          company_size?: string | null;
          sic_code?: string | null;
          metadata?: Json | null;
          companies_house_number?: string | null;
          sic_codes?: string[] | null;
          company_status?: string | null;
          date_of_creation?: string | null;
          registered_address?: Json | null;
          enriched_at?: string | null;
        };
      };
      jobs: {
        Row: {
          id: number;
          source_id: number;
          external_id: string;
          source_url: string;
          title: string;
          description: string;
          description_plain: string | null;
          company_id: number | null;
          company_name: string;
          location_raw: string | null;
          location_city: string | null;
          location_region: string | null;
          location_postcode: string | null;
          location_type: string | null;
          location: unknown | null;
          employment_type: string[] | null;
          seniority_level: string | null;
          visa_sponsorship: string | null;
          salary_min: number | null;
          salary_max: number | null;
          salary_currency: string | null;
          salary_period: string | null;
          salary_raw: string | null;
          salary_annual_min: number | null;
          salary_annual_max: number | null;
          salary_is_predicted: boolean | null;
          salary_predicted_min: number | null;
          salary_predicted_max: number | null;
          salary_confidence: number | null;
          salary_model_version: string | null;
          category: string | null;
          category_raw: string | null;
          contract_type: string | null;
          soc_code: string | null;
          esco_occupation_uri: string | null;
          date_posted: string;
          date_expires: string | null;
          date_crawled: string | null;
          status: string | null;
          retry_count: number | null;
          last_error: string | null;
          structured_summary: string | null;
          failed_stage: string | null;
          search_vector: unknown | null;
          embedding: unknown | null;
          canonical_id: number | null;
          is_duplicate: boolean | null;
          duplicate_score: number | null;
          content_hash: string | null;
          description_hash: string | null;
          raw_data: Json | null;
        };
        Insert: {
          id?: never;
          source_id: number;
          external_id: string;
          source_url: string;
          title: string;
          description: string;
          description_plain?: string | null;
          company_id?: number | null;
          company_name: string;
          location_raw?: string | null;
          location_city?: string | null;
          location_region?: string | null;
          location_postcode?: string | null;
          location_type?: string | null;
          location?: unknown | null;
          employment_type?: string[] | null;
          seniority_level?: string | null;
          visa_sponsorship?: string | null;
          salary_min?: number | null;
          salary_max?: number | null;
          salary_currency?: string | null;
          salary_period?: string | null;
          salary_raw?: string | null;
          salary_annual_min?: number | null;
          salary_annual_max?: number | null;
          salary_is_predicted?: boolean | null;
          salary_predicted_min?: number | null;
          salary_predicted_max?: number | null;
          salary_confidence?: number | null;
          salary_model_version?: string | null;
          category?: string | null;
          category_raw?: string | null;
          contract_type?: string | null;
          soc_code?: string | null;
          esco_occupation_uri?: string | null;
          date_posted: string;
          date_expires?: string | null;
          date_crawled?: string | null;
          status?: string | null;
          retry_count?: number | null;
          last_error?: string | null;
          structured_summary?: string | null;
          failed_stage?: string | null;
          embedding?: unknown | null;
          canonical_id?: number | null;
          is_duplicate?: boolean | null;
          duplicate_score?: number | null;
          content_hash?: string | null;
          description_hash?: string | null;
          raw_data?: Json | null;
        };
        Update: {
          id?: never;
          source_id?: number;
          external_id?: string;
          source_url?: string;
          title?: string;
          description?: string;
          description_plain?: string | null;
          company_id?: number | null;
          company_name?: string;
          location_raw?: string | null;
          location_city?: string | null;
          location_region?: string | null;
          location_postcode?: string | null;
          location_type?: string | null;
          location?: unknown | null;
          employment_type?: string[] | null;
          seniority_level?: string | null;
          visa_sponsorship?: string | null;
          salary_min?: number | null;
          salary_max?: number | null;
          salary_currency?: string | null;
          salary_period?: string | null;
          salary_raw?: string | null;
          salary_annual_min?: number | null;
          salary_annual_max?: number | null;
          salary_is_predicted?: boolean | null;
          salary_predicted_min?: number | null;
          salary_predicted_max?: number | null;
          salary_confidence?: number | null;
          salary_model_version?: string | null;
          category?: string | null;
          category_raw?: string | null;
          contract_type?: string | null;
          soc_code?: string | null;
          esco_occupation_uri?: string | null;
          date_posted?: string;
          date_expires?: string | null;
          date_crawled?: string | null;
          status?: string | null;
          retry_count?: number | null;
          last_error?: string | null;
          structured_summary?: string | null;
          failed_stage?: string | null;
          embedding?: unknown | null;
          canonical_id?: number | null;
          is_duplicate?: boolean | null;
          duplicate_score?: number | null;
          content_hash?: string | null;
          description_hash?: string | null;
          raw_data?: Json | null;
        };
      };
      skills: {
        Row: {
          id: number;
          name: string;
          esco_uri: string | null;
          lightcast_id: string | null;
          skill_type: string | null;
          category: string | null;
          source: string | null;
          aliases: string[] | null;
        };
        Insert: {
          id?: never;
          name: string;
          esco_uri?: string | null;
          lightcast_id?: string | null;
          skill_type?: string | null;
          category?: string | null;
          source?: string | null;
          aliases?: string[] | null;
        };
        Update: {
          id?: never;
          name?: string;
          esco_uri?: string | null;
          lightcast_id?: string | null;
          skill_type?: string | null;
          category?: string | null;
          source?: string | null;
          aliases?: string[] | null;
        };
      };
      job_skills: {
        Row: {
          job_id: number;
          skill_id: number;
          confidence: number | null;
          is_required: boolean | null;
        };
        Insert: {
          job_id: number;
          skill_id: number;
          confidence?: number | null;
          is_required?: boolean | null;
        };
        Update: {
          job_id?: number;
          skill_id?: number;
          confidence?: number | null;
          is_required?: boolean | null;
        };
      };
      esco_skills: {
        Row: {
          concept_uri: string;
          preferred_label: string;
          alt_labels: string[] | null;
          skill_type: string | null;
          description: string | null;
          isco_group: string | null;
        };
        Insert: {
          concept_uri: string;
          preferred_label: string;
          alt_labels?: string[] | null;
          skill_type?: string | null;
          description?: string | null;
          isco_group?: string | null;
        };
        Update: {
          concept_uri?: string;
          preferred_label?: string;
          alt_labels?: string[] | null;
          skill_type?: string | null;
          description?: string | null;
          isco_group?: string | null;
        };
      };
      user_profiles: {
        Row: {
          id: string;
          target_role: string | null;
          skills: string[] | null;
          experience_text: string | null;
          preferred_location: string | null;
          preferred_lat: number | null;
          preferred_lng: number | null;
          work_preference: string | null;
          min_salary: number | null;
          profile_embedding: unknown | null;
          profile_text: string | null;
          updated_at: string | null;
        };
        Insert: {
          id: string;
          target_role?: string | null;
          skills?: string[] | null;
          experience_text?: string | null;
          preferred_location?: string | null;
          preferred_lat?: number | null;
          preferred_lng?: number | null;
          work_preference?: string | null;
          min_salary?: number | null;
          profile_embedding?: unknown | null;
          profile_text?: string | null;
          updated_at?: string | null;
        };
        Update: {
          id?: string;
          target_role?: string | null;
          skills?: string[] | null;
          experience_text?: string | null;
          preferred_location?: string | null;
          preferred_lat?: number | null;
          preferred_lng?: number | null;
          work_preference?: string | null;
          min_salary?: number | null;
          profile_embedding?: unknown | null;
          profile_text?: string | null;
          updated_at?: string | null;
        };
      };
      ai_decision_audit_log: {
        Row: {
          id: number;
          created_at: string;
          decision_type: string;
          model_provider: string;
          model_version: string;
          input_hash: string;
          input_summary: string | null;
          output_summary: string;
          confidence: number | null;
          user_id: string | null;
          job_id: number | null;
          session_id: string | null;
          latency_ms: number | null;
          token_count: number | null;
          cost_usd: number | null;
          requires_review: boolean | null;
          reviewed_at: string | null;
          reviewed_by: string | null;
          review_outcome: string | null;
        };
        Insert: {
          id?: never;
          created_at?: string;
          decision_type: string;
          model_provider: string;
          model_version: string;
          input_hash: string;
          input_summary?: string | null;
          output_summary: string;
          confidence?: number | null;
          user_id?: string | null;
          job_id?: number | null;
          session_id?: string | null;
          latency_ms?: number | null;
          token_count?: number | null;
          cost_usd?: number | null;
          requires_review?: boolean | null;
          reviewed_at?: string | null;
          reviewed_by?: string | null;
          review_outcome?: string | null;
        };
        Update: {
          id?: never;
          created_at?: string;
          decision_type?: string;
          model_provider?: string;
          model_version?: string;
          input_hash?: string;
          input_summary?: string | null;
          output_summary?: string;
          confidence?: number | null;
          user_id?: string | null;
          job_id?: number | null;
          session_id?: string | null;
          latency_ms?: number | null;
          token_count?: number | null;
          cost_usd?: number | null;
          requires_review?: boolean | null;
          reviewed_at?: string | null;
          reviewed_by?: string | null;
          review_outcome?: string | null;
        };
      };
    };
    Views: {
      mv_search_facets: {
        Row: {
          facet_type: string;
          facet_value: string | null;
          job_count: number;
        };
      };
      mv_salary_histogram: {
        Row: {
          bucket: number | null;
          job_count: number;
          bucket_min: number | null;
          bucket_max: number | null;
        };
      };
    };
    Functions: {
      search_jobs: {
        Args: {
          query_text?: string;
          query_embedding?: string;
          match_limit?: number;
          lat?: number;
          lng?: number;
          radius_miles?: number;
        };
        Returns: {
          id: number;
          title: string;
          company_name: string;
          description_plain: string | null;
          location_city: string | null;
          location_type: string | null;
          salary_annual_min: number | null;
          salary_annual_max: number | null;
          employment_type: string[] | null;
          date_posted: string;
          source_url: string;
          rrf_score: number;
        }[];
      };
      search_jobs_v2: {
        Args: {
          query_text?: string;
          query_embedding?: string;
          match_limit?: number;
          lat?: number;
          lng?: number;
          radius_miles?: number;
          min_salary?: number;
          max_salary?: number;
          work_type?: string;
          category_filter?: string;
          seniority_filter?: string;
          skill_names?: string[];
          exclude_duplicates?: boolean;
          date_posted_after?: string;
        };
        Returns: {
          id: number;
          title: string;
          company_name: string;
          description_plain: string | null;
          location_city: string | null;
          location_region: string | null;
          location_type: string | null;
          salary_annual_min: number | null;
          salary_annual_max: number | null;
          salary_predicted_min: number | null;
          salary_predicted_max: number | null;
          salary_is_predicted: boolean | null;
          employment_type: string[] | null;
          seniority_level: string | null;
          category: string | null;
          date_posted: string;
          source_url: string;
          rrf_score: number;
        }[];
      };
    };
    Enums: Record<string, never>;
  };
}
