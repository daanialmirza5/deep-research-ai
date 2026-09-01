-- Generated reference snapshot — NOT the migration source of truth.
-- The real, versioned source of truth is backend/alembic/versions/; this
-- file is a human-readable dump of what `alembic upgrade head` produces,
-- kept for quick schema review in a PR without reading Alembic diff syntax.
-- Regenerate after any migration change:
--   pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > database/schema.sql
--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_runs (
    session_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    status character varying(20) NOT NULL,
    input_state jsonb,
    output_state jsonb,
    duration_ms integer,
    retry_count integer NOT NULL,
    error text,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_agent_runs_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    name character varying(100) NOT NULL,
    type character varying(100) NOT NULL,
    description text,
    config jsonb NOT NULL,
    is_enabled boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: analytics_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analytics_events (
    user_id uuid,
    session_id uuid,
    event_type character varying(100) NOT NULL,
    payload jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    user_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    encrypted_key character varying NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: citations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.citations (
    report_id uuid NOT NULL,
    source_type character varying(50) NOT NULL,
    title character varying(1000) NOT NULL,
    authors character varying(1000),
    url character varying(2000),
    doi character varying(200),
    year integer,
    citation_style character varying(10) NOT NULL,
    formatted_citation text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_citations_citation_style CHECK (((citation_style)::text = ANY ((ARRAY['apa'::character varying, 'mla'::character varying, 'ieee'::character varying])::text[])))
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    project_id uuid NOT NULL,
    uploaded_by uuid NOT NULL,
    source_type character varying(20) NOT NULL,
    original_filename character varying(500),
    storage_path character varying(1000) NOT NULL,
    mime_type character varying(200),
    size_bytes bigint,
    status character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_documents_source_type CHECK (((source_type)::text = ANY ((ARRAY['pdf'::character varying, 'docx'::character varying, 'txt'::character varying, 'csv'::character varying, 'markdown'::character varying, 'url'::character varying, 'youtube'::character varying])::text[]))),
    CONSTRAINT ck_documents_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'indexed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.embeddings (
    document_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    chunk_text text NOT NULL,
    embedding public.vector(1024) NOT NULL,
    metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    session_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    agent_metadata jsonb,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_messages_role CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying, 'agent'::character varying])::text[])))
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    owner_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    status character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_projects_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying])::text[])))
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: report_exports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_exports (
    report_id uuid NOT NULL,
    format character varying(20) NOT NULL,
    storage_path character varying(1000) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_report_exports_format CHECK (((format)::text = ANY ((ARRAY['markdown'::character varying, 'pdf'::character varying, 'docx'::character varying, 'html'::character varying])::text[])))
);


--
-- Name: reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reports (
    session_id uuid NOT NULL,
    title character varying(500) NOT NULL,
    content_markdown text NOT NULL,
    quality_score double precision,
    status character varying(20) NOT NULL,
    version integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_reports_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'superseded'::character varying])::text[])))
);


--
-- Name: research_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.research_sessions (
    project_id uuid NOT NULL,
    user_id uuid NOT NULL,
    query text NOT NULL,
    status character varying(30) NOT NULL,
    graph_state jsonb,
    revision_count integer NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_research_sessions_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'awaiting_revision'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: search_queries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.search_queries (
    session_id uuid NOT NULL,
    source character varying(50) NOT NULL,
    query_text text NOT NULL,
    raw_results jsonb,
    result_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    email character varying(320) NOT NULL,
    hashed_password character varying,
    full_name character varying(200) NOT NULL,
    oauth_provider character varying(50),
    oauth_id character varying(255),
    role character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT ck_users_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'member'::character varying])::text[])))
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: agent_runs pk_agent_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_runs
    ADD CONSTRAINT pk_agent_runs PRIMARY KEY (id);


--
-- Name: agents pk_agents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT pk_agents PRIMARY KEY (id);


--
-- Name: analytics_events pk_analytics_events; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT pk_analytics_events PRIMARY KEY (id);


--
-- Name: api_keys pk_api_keys; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT pk_api_keys PRIMARY KEY (id);


--
-- Name: citations pk_citations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT pk_citations PRIMARY KEY (id);


--
-- Name: documents pk_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT pk_documents PRIMARY KEY (id);


--
-- Name: embeddings pk_embeddings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.embeddings
    ADD CONSTRAINT pk_embeddings PRIMARY KEY (id);


--
-- Name: messages pk_messages; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT pk_messages PRIMARY KEY (id);


--
-- Name: projects pk_projects; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT pk_projects PRIMARY KEY (id);


--
-- Name: refresh_tokens pk_refresh_tokens; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT pk_refresh_tokens PRIMARY KEY (id);


--
-- Name: report_exports pk_report_exports; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_exports
    ADD CONSTRAINT pk_report_exports PRIMARY KEY (id);


--
-- Name: reports pk_reports; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT pk_reports PRIMARY KEY (id);


--
-- Name: research_sessions pk_research_sessions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_sessions
    ADD CONSTRAINT pk_research_sessions PRIMARY KEY (id);


--
-- Name: search_queries pk_search_queries; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_queries
    ADD CONSTRAINT pk_search_queries PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: agents uq_agents_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT uq_agents_name UNIQUE (name);


--
-- Name: refresh_tokens uq_refresh_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash);


--
-- Name: ix_agent_runs_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_runs_session_id ON public.agent_runs USING btree (session_id);


--
-- Name: ix_analytics_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analytics_events_event_type ON public.analytics_events USING btree (event_type);


--
-- Name: ix_analytics_events_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analytics_events_session_id ON public.analytics_events USING btree (session_id);


--
-- Name: ix_analytics_events_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_analytics_events_user_id ON public.analytics_events USING btree (user_id);


--
-- Name: ix_api_keys_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_keys_user_id ON public.api_keys USING btree (user_id);


--
-- Name: ix_citations_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_citations_report_id ON public.citations USING btree (report_id);


--
-- Name: ix_documents_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_project_id ON public.documents USING btree (project_id);


--
-- Name: ix_embeddings_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_embeddings_document_id ON public.embeddings USING btree (document_id);


--
-- Name: ix_embeddings_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_embeddings_embedding_hnsw ON public.embeddings USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_messages_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_messages_session_id ON public.messages USING btree (session_id);


--
-- Name: ix_projects_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_projects_owner_id ON public.projects USING btree (owner_id);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_report_exports_report_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_exports_report_id ON public.report_exports USING btree (report_id);


--
-- Name: ix_reports_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reports_session_id ON public.reports USING btree (session_id);


--
-- Name: ix_research_sessions_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_research_sessions_project_id ON public.research_sessions USING btree (project_id);


--
-- Name: ix_research_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_research_sessions_user_id ON public.research_sessions USING btree (user_id);


--
-- Name: ix_search_queries_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_queries_session_id ON public.search_queries USING btree (session_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: agent_runs fk_agent_runs_agent_id_agents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_runs
    ADD CONSTRAINT fk_agent_runs_agent_id_agents FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE RESTRICT;


--
-- Name: agent_runs fk_agent_runs_session_id_research_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_runs
    ADD CONSTRAINT fk_agent_runs_session_id_research_sessions FOREIGN KEY (session_id) REFERENCES public.research_sessions(id) ON DELETE CASCADE;


--
-- Name: analytics_events fk_analytics_events_session_id_research_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT fk_analytics_events_session_id_research_sessions FOREIGN KEY (session_id) REFERENCES public.research_sessions(id) ON DELETE SET NULL;


--
-- Name: analytics_events fk_analytics_events_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analytics_events
    ADD CONSTRAINT fk_analytics_events_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: api_keys fk_api_keys_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT fk_api_keys_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: citations fk_citations_report_id_reports; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT fk_citations_report_id_reports FOREIGN KEY (report_id) REFERENCES public.reports(id) ON DELETE CASCADE;


--
-- Name: documents fk_documents_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: documents fk_documents_uploaded_by_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT fk_documents_uploaded_by_users FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: embeddings fk_embeddings_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.embeddings
    ADD CONSTRAINT fk_embeddings_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: messages fk_messages_session_id_research_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT fk_messages_session_id_research_sessions FOREIGN KEY (session_id) REFERENCES public.research_sessions(id) ON DELETE CASCADE;


--
-- Name: projects fk_projects_owner_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT fk_projects_owner_id_users FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens fk_refresh_tokens_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: report_exports fk_report_exports_report_id_reports; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_exports
    ADD CONSTRAINT fk_report_exports_report_id_reports FOREIGN KEY (report_id) REFERENCES public.reports(id) ON DELETE CASCADE;


--
-- Name: reports fk_reports_session_id_research_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT fk_reports_session_id_research_sessions FOREIGN KEY (session_id) REFERENCES public.research_sessions(id) ON DELETE CASCADE;


--
-- Name: research_sessions fk_research_sessions_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_sessions
    ADD CONSTRAINT fk_research_sessions_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: research_sessions fk_research_sessions_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_sessions
    ADD CONSTRAINT fk_research_sessions_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: search_queries fk_search_queries_session_id_research_sessions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_queries
    ADD CONSTRAINT fk_search_queries_session_id_research_sessions FOREIGN KEY (session_id) REFERENCES public.research_sessions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

