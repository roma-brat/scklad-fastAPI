--
-- PostgreSQL database dump
--

\restrict YH0Uf9D4cJE3MeTmB6tbCkgMRBXVBJ0c35Vu9T7PqNAsEASAd4eSrFDo5LEGhnx

-- Dumped from database version 16.13 (Homebrew)
-- Dumped by pg_dump version 16.13 (Homebrew)

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
-- Name: force_update_user_role(integer, text); Type: FUNCTION; Schema: public; Owner: sklad_user
--

CREATE FUNCTION public.force_update_user_role(p_user_id integer, p_role text) RETURNS void
    LANGUAGE plpgsql
    AS $$
            DECLARE
                rec RECORD;
            BEGIN
                -- Get current user data
                SELECT * INTO rec FROM users WHERE id = p_user_id;
                
                -- Delete old record
                DELETE FROM users WHERE id = p_user_id;
                
                -- Insert with new role (bypass constraint)
                INSERT INTO users (id, username, password_hash, role, workstation, is_active, created_at, updated_at)
                VALUES (rec.id, rec.username, rec.password_hash, p_role, rec.workstation, rec.is_active, rec.created_at, NOW());
            END
            $$;


ALTER FUNCTION public.force_update_user_role(p_user_id integer, p_role text) OWNER TO sklad_user;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: romanbratuskin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO romanbratuskin;

--
-- Name: update_user_role(integer, text); Type: FUNCTION; Schema: public; Owner: sklad_user
--

CREATE FUNCTION public.update_user_role(p_user_id integer, p_role text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
            BEGIN
                UPDATE users SET role = p_role, updated_at = NOW() 
                WHERE id = p_user_id;
            END
            $$;


ALTER FUNCTION public.update_user_role(p_user_id integer, p_role text) OWNER TO sklad_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    user_id integer,
    action character varying(100) NOT NULL,
    entity_type character varying(50),
    entity_id integer,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.audit_log OWNER TO romanbratuskin;

--
-- Name: TABLE audit_log; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON TABLE public.audit_log IS 'Журнал аудита всех действий в системе';


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_log_id_seq OWNER TO romanbratuskin;

--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: batch_counter; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.batch_counter (
    id integer NOT NULL,
    prefix character varying(5) NOT NULL,
    last_number integer DEFAULT 0
);


ALTER TABLE public.batch_counter OWNER TO romanbratushkin;

--
-- Name: batch_counter_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.batch_counter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.batch_counter_id_seq OWNER TO romanbratushkin;

--
-- Name: batch_counter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.batch_counter_id_seq OWNED BY public.batch_counter.id;


--
-- Name: calendar_configs; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.calendar_configs (
    id integer NOT NULL,
    user_id integer NOT NULL,
    config_key character varying(50) NOT NULL,
    visible_equipment text,
    equipment_order text,
    panel_visible boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.calendar_configs OWNER TO romanbratushkin;

--
-- Name: calendar_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.calendar_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calendar_configs_id_seq OWNER TO romanbratushkin;

--
-- Name: calendar_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.calendar_configs_id_seq OWNED BY public.calendar_configs.id;


--
-- Name: cooperatives; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.cooperatives (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255),
    is_active integer DEFAULT 1
);


ALTER TABLE public.cooperatives OWNER TO sklad_user;

--
-- Name: cooperatives_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.cooperatives_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cooperatives_id_seq OWNER TO sklad_user;

--
-- Name: cooperatives_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.cooperatives_id_seq OWNED BY public.cooperatives.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id integer,
    item_id integer,
    quantity integer NOT NULL,
    operation_type character varying(20) NOT NULL,
    detail character varying(255),
    reason character varying(255),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT transactions_operation_type_check CHECK (((operation_type)::text = ANY ((ARRAY['income'::character varying, 'expense'::character varying, 'adjustment'::character varying])::text[])))
);


ALTER TABLE public.transactions OWNER TO romanbratuskin;

--
-- Name: TABLE transactions; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON TABLE public.transactions IS 'Журнал операций (приход/расход)';


--
-- Name: COLUMN transactions.operation_type; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON COLUMN public.transactions.operation_type IS 'Тип: income, expense, adjustment';


--
-- Name: daily_transaction_stats; Type: VIEW; Schema: public; Owner: romanbratuskin
--

CREATE VIEW public.daily_transaction_stats AS
 SELECT date("timestamp") AS date,
    operation_type,
    count(*) AS operation_count,
    sum(quantity) AS total_quantity
   FROM public.transactions
  GROUP BY (date("timestamp")), operation_type
  ORDER BY (date("timestamp")) DESC;


ALTER VIEW public.daily_transaction_stats OWNER TO romanbratuskin;

--
-- Name: detail_routes; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.detail_routes (
    id integer NOT NULL,
    detail_name character varying(255) NOT NULL,
    designation character varying(100),
    material_instance_id integer,
    pdf_file character varying(500),
    status character varying(50) DEFAULT 'черновик'::character varying,
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    quantity integer DEFAULT 1,
    pdf_path character varying(500),
    pdf_data bytea,
    length double precision,
    diameter double precision,
    preprocessing_data text,
    version character varying(50),
    approved boolean DEFAULT false,
    detail_id integer,
    app_id character varying(50),
    lotzman_id character varying(50),
    is_actual boolean DEFAULT true,
    dimension1 double precision,
    dimension2 double precision,
    parts_per_blank integer DEFAULT 1,
    waste_percent double precision DEFAULT 0,
    preprocessing boolean DEFAULT false,
    primitive_form_id character varying(50),
    prim_dim1 double precision,
    prim_dim2 double precision,
    prim_dim3 double precision,
    lot_size integer DEFAULT 1,
    file character varying(500),
    change_indicator boolean DEFAULT false,
    volume double precision,
    calculated_mass double precision,
    blank_cost double precision,
    manual_mass_input boolean DEFAULT false,
    material_cost double precision,
    unit_cost double precision,
    labor_cost double precision,
    depreciation_cost double precision,
    utility_cost double precision,
    dimensions character varying(100),
    preprocessing_dimensions character varying(200),
    name character varying(255)
);


ALTER TABLE public.detail_routes OWNER TO sklad_user;

--
-- Name: detail_routes_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.detail_routes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detail_routes_id_seq OWNER TO sklad_user;

--
-- Name: detail_routes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.detail_routes_id_seq OWNED BY public.detail_routes.id;


--
-- Name: details; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.details (
    id integer NOT NULL,
    detail_id character varying(50) NOT NULL,
    lotzman_id character varying(50),
    detail_type character varying(50),
    designation character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    version double precision,
    is_actual boolean,
    drawing character varying(500),
    correct_designation boolean,
    creator_id integer,
    created_at timestamp without time zone
);


ALTER TABLE public.details OWNER TO romanbratushkin;

--
-- Name: details_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.details_id_seq OWNER TO romanbratushkin;

--
-- Name: details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.details_id_seq OWNED BY public.details.id;


--
-- Name: equipment; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.equipment (
    id integer NOT NULL,
    app_id character varying(50),
    name character varying(200) NOT NULL,
    inventory_number character varying(50),
    is_universal boolean DEFAULT false,
    operation_types character varying(500),
    wage_with_taxes double precision,
    multi_operational integer,
    power double precision,
    cost double precision,
    spi double precision,
    tool_cost double precision,
    tooling_cost double precision,
    maintenance_cost double precision,
    setup_cost double precision,
    created_at timestamp without time zone DEFAULT now(),
    operator_id integer,
    is_active boolean DEFAULT true,
    default_working_hours integer DEFAULT 7,
    "position" integer,
    has_workshop_inventory boolean DEFAULT false
);


ALTER TABLE public.equipment OWNER TO sklad_user;

--
-- Name: equipment_calendar; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.equipment_calendar (
    id integer NOT NULL,
    equipment_id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    working_hours integer,
    is_working boolean,
    notes character varying(255),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.equipment_calendar OWNER TO romanbratushkin;

--
-- Name: equipment_calendar_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.equipment_calendar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_calendar_id_seq OWNER TO romanbratushkin;

--
-- Name: equipment_calendar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.equipment_calendar_id_seq OWNED BY public.equipment_calendar.id;


--
-- Name: equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.equipment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_id_seq OWNER TO sklad_user;

--
-- Name: equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.equipment_id_seq OWNED BY public.equipment.id;


--
-- Name: equipment_instances; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.equipment_instances (
    id integer NOT NULL,
    app_id character varying(50),
    equipment_id character varying(50),
    lotzman_id character varying(50),
    number character varying(50),
    operator_id integer,
    notes character varying(500),
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.equipment_instances OWNER TO sklad_user;

--
-- Name: equipment_instances_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.equipment_instances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipment_instances_id_seq OWNER TO sklad_user;

--
-- Name: equipment_instances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.equipment_instances_id_seq OWNED BY public.equipment_instances.id;


--
-- Name: geometry; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.geometry (
    id integer NOT NULL,
    app_id character varying(50),
    name character varying(100) NOT NULL,
    primitive boolean DEFAULT false,
    prefix character varying(20),
    unit character varying(20),
    dimension1 character varying(50),
    dimension2 character varying(50),
    dimension3 character varying(50),
    for_volume boolean,
    sketch character varying(500),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.geometry OWNER TO sklad_user;

--
-- Name: geometry_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.geometry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.geometry_id_seq OWNER TO sklad_user;

--
-- Name: geometry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.geometry_id_seq OWNED BY public.geometry.id;


--
-- Name: inventory_changes; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.inventory_changes (
    id integer NOT NULL,
    item_id integer,
    old_quantity integer NOT NULL,
    new_quantity integer NOT NULL,
    changed_by integer,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.inventory_changes OWNER TO romanbratuskin;

--
-- Name: TABLE inventory_changes; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON TABLE public.inventory_changes IS 'История изменений остатков товаров';


--
-- Name: inventory_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.inventory_changes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inventory_changes_id_seq OWNER TO romanbratuskin;

--
-- Name: inventory_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.inventory_changes_id_seq OWNED BY public.inventory_changes.id;


--
-- Name: items; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.items (
    id integer NOT NULL,
    item_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    quantity integer DEFAULT 0 NOT NULL,
    min_stock integer DEFAULT 1 NOT NULL,
    category character varying(100),
    location character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    image_url text,
    shop_url text,
    specifications text
);


ALTER TABLE public.items OWNER TO romanbratuskin;

--
-- Name: TABLE items; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON TABLE public.items IS 'Товары/инструменты на складе';


--
-- Name: COLUMN items.item_id; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON COLUMN public.items.item_id IS 'Уникальный идентификатор товара (для QR-кода)';


--
-- Name: COLUMN items.min_stock; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON COLUMN public.items.min_stock IS 'Минимальный запас для уведомления';


--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.items_id_seq OWNER TO romanbratuskin;

--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.id;


--
-- Name: low_stock_items; Type: VIEW; Schema: public; Owner: romanbratuskin
--

CREATE VIEW public.low_stock_items AS
 SELECT id,
    item_id,
    name,
    quantity,
    min_stock,
    (min_stock - quantity) AS shortage
   FROM public.items
  WHERE (quantity <= min_stock);


ALTER VIEW public.low_stock_items OWNER TO romanbratuskin;

--
-- Name: material_instances; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.material_instances (
    id integer NOT NULL,
    app_id character varying(50),
    mark_id character varying(50),
    mark_name character varying(100),
    mark_gost character varying(100),
    sortament_id character varying(50),
    sortament_name character varying(100),
    sortament_gost character varying(100),
    dimension1 double precision,
    dimension2 double precision,
    dimension3 double precision,
    price_per_ton double precision,
    price_per_piece double precision,
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    lotzman_id character varying(50),
    volume_argument character varying(10),
    volume_value double precision,
    price_per_kg double precision,
    type_size character varying(100),
    dimensions character varying(200)
);


ALTER TABLE public.material_instances OWNER TO sklad_user;

--
-- Name: material_instances_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.material_instances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_instances_id_seq OWNER TO sklad_user;

--
-- Name: material_instances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.material_instances_id_seq OWNED BY public.material_instances.id;


--
-- Name: materials; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.materials (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255),
    unit character varying(20) DEFAULT 'шт'::character varying,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    app_id character varying(50),
    lotzman_id character varying(50),
    density double precision
);


ALTER TABLE public.materials OWNER TO romanbratuskin;

--
-- Name: materials_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.materials_id_seq OWNER TO romanbratuskin;

--
-- Name: materials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.materials_id_seq OWNED BY public.materials.id;


--
-- Name: operation_cooperative; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.operation_cooperative (
    id integer NOT NULL,
    operation_type_id integer,
    cooperative_id integer
);


ALTER TABLE public.operation_cooperative OWNER TO sklad_user;

--
-- Name: operation_cooperative_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.operation_cooperative_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.operation_cooperative_id_seq OWNER TO sklad_user;

--
-- Name: operation_cooperative_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.operation_cooperative_id_seq OWNED BY public.operation_cooperative.id;


--
-- Name: operation_equipment; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.operation_equipment (
    id integer NOT NULL,
    operation_type_id integer,
    equipment_id integer
);


ALTER TABLE public.operation_equipment OWNER TO sklad_user;

--
-- Name: operation_equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.operation_equipment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.operation_equipment_id_seq OWNER TO sklad_user;

--
-- Name: operation_equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.operation_equipment_id_seq OWNED BY public.operation_equipment.id;


--
-- Name: operation_types; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.operation_types (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255),
    default_duration integer DEFAULT 60,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.operation_types OWNER TO romanbratuskin;

--
-- Name: operation_types_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.operation_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.operation_types_id_seq OWNER TO romanbratuskin;

--
-- Name: operation_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.operation_types_id_seq OWNED BY public.operation_types.id;


--
-- Name: operation_workshop; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.operation_workshop (
    id integer NOT NULL,
    operation_type_id integer,
    workshop_id integer
);


ALTER TABLE public.operation_workshop OWNER TO sklad_user;

--
-- Name: operation_workshop_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.operation_workshop_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.operation_workshop_id_seq OWNER TO sklad_user;

--
-- Name: operation_workshop_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.operation_workshop_id_seq OWNED BY public.operation_workshop.id;


--
-- Name: order_priorities; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.order_priorities (
    id integer NOT NULL,
    order_id integer NOT NULL,
    priority integer,
    deadline timestamp without time zone,
    notes character varying(500),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.order_priorities OWNER TO romanbratushkin;

--
-- Name: order_priorities_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.order_priorities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_priorities_id_seq OWNER TO romanbratushkin;

--
-- Name: order_priorities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.order_priorities_id_seq OWNED BY public.order_priorities.id;


--
-- Name: order_schedule; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.order_schedule (
    id integer NOT NULL,
    order_id integer NOT NULL,
    equipment_name character varying(255),
    operation_name character varying(255),
    schedule_date date NOT NULL,
    parts integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.order_schedule OWNER TO romanbratushkin;

--
-- Name: order_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.order_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_schedule_id_seq OWNER TO romanbratushkin;

--
-- Name: order_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.order_schedule_id_seq OWNED BY public.order_schedule.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    route_id integer,
    quantity integer,
    blanks_needed integer,
    route_quantity integer,
    pdf_path character varying(500),
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    start_date character varying(20),
    end_date character varying(20),
    app_id character varying(50),
    id_1c character varying(50),
    order_number integer,
    lot_size integer,
    file character varying(500),
    status character varying(50) DEFAULT 'новый'::character varying,
    in_progress boolean DEFAULT false,
    blanks_quantity integer,
    blank_size character varying(100),
    preprocessing_size character varying(200),
    updated_at timestamp without time zone,
    production_type character varying(20) DEFAULT 'piece'::character varying,
    batch_number character varying(50),
    manual_detail_name character varying(255),
    manual_quantity integer,
    designation character varying(100),
    detail_name character varying(255),
    mark_name character varying(100),
    sortament_name character varying(100),
    route_card_data jsonb
);


ALTER TABLE public.orders OWNER TO romanbratushkin;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO romanbratushkin;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: planning_rules; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.planning_rules (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    value text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.planning_rules OWNER TO sklad_user;

--
-- Name: planning_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.planning_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.planning_rules_id_seq OWNER TO sklad_user;

--
-- Name: planning_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.planning_rules_id_seq OWNED BY public.planning_rules.id;


--
-- Name: production_schedule; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.production_schedule (
    id integer NOT NULL,
    order_id integer NOT NULL,
    route_operation_id integer,
    equipment_id integer,
    planned_date timestamp without time zone,
    actual_date timestamp without time zone,
    status character varying(20),
    priority integer,
    quantity integer,
    duration_minutes integer,
    notes character varying(500),
    is_manual_override boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    taken_at timestamp without time zone,
    completed_at timestamp without time zone,
    taken_by character varying(100),
    completed_by character varying(100),
    is_cooperation boolean DEFAULT false,
    coop_company_name character varying(255),
    coop_duration_days integer
);


ALTER TABLE public.production_schedule OWNER TO romanbratushkin;

--
-- Name: production_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.production_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.production_schedule_id_seq OWNER TO romanbratushkin;

--
-- Name: production_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.production_schedule_id_seq OWNED BY public.production_schedule.id;


--
-- Name: route_operations; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.route_operations (
    id integer NOT NULL,
    route_id integer,
    operation_type_id integer,
    equipment_id integer,
    sequence_number integer NOT NULL,
    duration_minutes integer,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    workshop_id integer,
    is_cooperation boolean DEFAULT false,
    prep_time integer DEFAULT 0,
    control_time integer DEFAULT 0,
    parts_count integer DEFAULT 1,
    coop_company_id integer,
    app_id character varying(50),
    workshop_area_id integer,
    equipment_instance_id character varying(50),
    fixture_id character varying(50),
    cost_logistics double precision,
    cost_operation double precision,
    previous_operation_id character varying(50),
    next_operation_id character varying(50),
    total_time integer DEFAULT 0,
    coop_duration_days integer DEFAULT 0,
    coop_position character varying(20) DEFAULT 'start'::character varying
);


ALTER TABLE public.route_operations OWNER TO sklad_user;

--
-- Name: route_operations_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.route_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.route_operations_id_seq OWNER TO sklad_user;

--
-- Name: route_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.route_operations_id_seq OWNED BY public.route_operations.id;


--
-- Name: schedule_events; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.schedule_events (
    id integer NOT NULL,
    schedule_id integer NOT NULL,
    event_type character varying(30) NOT NULL,
    created_at timestamp without time zone,
    created_by character varying(100)
);


ALTER TABLE public.schedule_events OWNER TO sklad_user;

--
-- Name: schedule_events_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.schedule_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.schedule_events_id_seq OWNER TO sklad_user;

--
-- Name: schedule_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.schedule_events_id_seq OWNED BY public.schedule_events.id;


--
-- Name: sortament; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.sortament (
    id integer NOT NULL,
    app_id character varying(50),
    name character varying(100) NOT NULL,
    gost character varying(100),
    geometry_id character varying(50),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.sortament OWNER TO sklad_user;

--
-- Name: sortament_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.sortament_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sortament_id_seq OWNER TO sklad_user;

--
-- Name: sortament_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.sortament_id_seq OWNED BY public.sortament.id;


--
-- Name: system_parameters; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.system_parameters (
    id integer NOT NULL,
    app_id character varying(50),
    name character varying(100) NOT NULL,
    value text,
    description character varying(255),
    param_type character varying(50),
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.system_parameters OWNER TO sklad_user;

--
-- Name: system_parameters_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.system_parameters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_parameters_id_seq OWNER TO sklad_user;

--
-- Name: system_parameters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.system_parameters_id_seq OWNED BY public.system_parameters.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.tasks (
    id integer NOT NULL,
    app_id character varying(50),
    order_id integer,
    operation_id character varying(50),
    is_cooperation boolean DEFAULT false,
    coop_company_id integer,
    workshop_id integer,
    workshop_area_id integer,
    sequence_number integer,
    operation_type_id integer,
    equipment_instance_id character varying(50),
    prep_time integer,
    duration_minutes integer,
    control_time integer,
    parts_count integer DEFAULT 1,
    notes character varying(500),
    status character varying(50) DEFAULT 'planned'::character varying,
    planned_date timestamp without time zone,
    actual_date timestamp without time zone,
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.tasks OWNER TO romanbratushkin;

--
-- Name: tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tasks_id_seq OWNER TO romanbratushkin;

--
-- Name: tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;


--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO romanbratuskin;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: user_items; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.user_items (
    id integer NOT NULL,
    user_id integer,
    item_id integer,
    quantity integer NOT NULL,
    taken_at timestamp without time zone
);


ALTER TABLE public.user_items OWNER TO romanbratushkin;

--
-- Name: user_items_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.user_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_items_id_seq OWNER TO romanbratushkin;

--
-- Name: user_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.user_items_id_seq OWNED BY public.user_items.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) DEFAULT 'user'::character varying NOT NULL,
    workstation character varying(100),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    workstations character varying(500),
    screen_permissions text,
    login character varying(50) NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'storekeeper'::character varying, 'user'::character varying, 'technologist'::character varying, 'foreman'::character varying, 'master'::character varying, 'chief_designer'::character varying, 'chief_engineer'::character varying, 'technologist_designer'::character varying, 'otk'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO romanbratuskin;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON TABLE public.users IS 'Пользователи системы';


--
-- Name: COLUMN users.role; Type: COMMENT; Schema: public; Owner: romanbratuskin
--

COMMENT ON COLUMN public.users.role IS 'Роль: admin, storekeeper, technologist, user';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO romanbratuskin;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: workshop_areas; Type: TABLE; Schema: public; Owner: sklad_user
--

CREATE TABLE public.workshop_areas (
    id integer NOT NULL,
    app_id character varying(50),
    lotzman_id character varying(50),
    workshop_id integer,
    designation character varying(50),
    name character varying(100),
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.workshop_areas OWNER TO sklad_user;

--
-- Name: workshop_areas_id_seq; Type: SEQUENCE; Schema: public; Owner: sklad_user
--

CREATE SEQUENCE public.workshop_areas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshop_areas_id_seq OWNER TO sklad_user;

--
-- Name: workshop_areas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sklad_user
--

ALTER SEQUENCE public.workshop_areas_id_seq OWNED BY public.workshop_areas.id;


--
-- Name: workshop_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.workshop_inventory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshop_inventory_id_seq OWNER TO romanbratushkin;

--
-- Name: workshop_inventory; Type: TABLE; Schema: public; Owner: romanbratushkin
--

CREATE TABLE public.workshop_inventory (
    id integer DEFAULT nextval('public.workshop_inventory_id_seq'::regclass) NOT NULL,
    equipment_id integer NOT NULL,
    item_id integer,
    quantity integer DEFAULT 1 NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.workshop_inventory OWNER TO romanbratushkin;

--
-- Name: workshop_inventory_new_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratushkin
--

CREATE SEQUENCE public.workshop_inventory_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshop_inventory_new_id_seq OWNER TO romanbratushkin;

--
-- Name: workshop_inventory_new_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratushkin
--

ALTER SEQUENCE public.workshop_inventory_new_id_seq OWNED BY public.workshop_inventory.id;


--
-- Name: workshops; Type: TABLE; Schema: public; Owner: romanbratuskin
--

CREATE TABLE public.workshops (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(255),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.workshops OWNER TO romanbratuskin;

--
-- Name: workshops_id_seq; Type: SEQUENCE; Schema: public; Owner: romanbratuskin
--

CREATE SEQUENCE public.workshops_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshops_id_seq OWNER TO romanbratuskin;

--
-- Name: workshops_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: romanbratuskin
--

ALTER SEQUENCE public.workshops_id_seq OWNED BY public.workshops.id;


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: batch_counter id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.batch_counter ALTER COLUMN id SET DEFAULT nextval('public.batch_counter_id_seq'::regclass);


--
-- Name: calendar_configs id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.calendar_configs ALTER COLUMN id SET DEFAULT nextval('public.calendar_configs_id_seq'::regclass);


--
-- Name: cooperatives id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.cooperatives ALTER COLUMN id SET DEFAULT nextval('public.cooperatives_id_seq'::regclass);


--
-- Name: detail_routes id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.detail_routes ALTER COLUMN id SET DEFAULT nextval('public.detail_routes_id_seq'::regclass);


--
-- Name: details id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.details ALTER COLUMN id SET DEFAULT nextval('public.details_id_seq'::regclass);


--
-- Name: equipment id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment ALTER COLUMN id SET DEFAULT nextval('public.equipment_id_seq'::regclass);


--
-- Name: equipment_calendar id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.equipment_calendar ALTER COLUMN id SET DEFAULT nextval('public.equipment_calendar_id_seq'::regclass);


--
-- Name: equipment_instances id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment_instances ALTER COLUMN id SET DEFAULT nextval('public.equipment_instances_id_seq'::regclass);


--
-- Name: geometry id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.geometry ALTER COLUMN id SET DEFAULT nextval('public.geometry_id_seq'::regclass);


--
-- Name: inventory_changes id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.inventory_changes ALTER COLUMN id SET DEFAULT nextval('public.inventory_changes_id_seq'::regclass);


--
-- Name: items id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.items ALTER COLUMN id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Name: material_instances id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.material_instances ALTER COLUMN id SET DEFAULT nextval('public.material_instances_id_seq'::regclass);


--
-- Name: materials id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.materials ALTER COLUMN id SET DEFAULT nextval('public.materials_id_seq'::regclass);


--
-- Name: operation_cooperative id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_cooperative ALTER COLUMN id SET DEFAULT nextval('public.operation_cooperative_id_seq'::regclass);


--
-- Name: operation_equipment id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_equipment ALTER COLUMN id SET DEFAULT nextval('public.operation_equipment_id_seq'::regclass);


--
-- Name: operation_types id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.operation_types ALTER COLUMN id SET DEFAULT nextval('public.operation_types_id_seq'::regclass);


--
-- Name: operation_workshop id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_workshop ALTER COLUMN id SET DEFAULT nextval('public.operation_workshop_id_seq'::regclass);


--
-- Name: order_priorities id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_priorities ALTER COLUMN id SET DEFAULT nextval('public.order_priorities_id_seq'::regclass);


--
-- Name: order_schedule id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_schedule ALTER COLUMN id SET DEFAULT nextval('public.order_schedule_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: planning_rules id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.planning_rules ALTER COLUMN id SET DEFAULT nextval('public.planning_rules_id_seq'::regclass);


--
-- Name: production_schedule id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.production_schedule ALTER COLUMN id SET DEFAULT nextval('public.production_schedule_id_seq'::regclass);


--
-- Name: route_operations id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.route_operations ALTER COLUMN id SET DEFAULT nextval('public.route_operations_id_seq'::regclass);


--
-- Name: schedule_events id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.schedule_events ALTER COLUMN id SET DEFAULT nextval('public.schedule_events_id_seq'::regclass);


--
-- Name: sortament id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.sortament ALTER COLUMN id SET DEFAULT nextval('public.sortament_id_seq'::regclass);


--
-- Name: system_parameters id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.system_parameters ALTER COLUMN id SET DEFAULT nextval('public.system_parameters_id_seq'::regclass);


--
-- Name: tasks id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: user_items id; Type: DEFAULT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.user_items ALTER COLUMN id SET DEFAULT nextval('public.user_items_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: workshop_areas id; Type: DEFAULT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.workshop_areas ALTER COLUMN id SET DEFAULT nextval('public.workshop_areas_id_seq'::regclass);


--
-- Name: workshops id; Type: DEFAULT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.workshops ALTER COLUMN id SET DEFAULT nextval('public.workshops_id_seq'::regclass);


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.audit_log (id, user_id, action, entity_type, entity_id, old_values, new_values, ip_address, "timestamp") FROM stdin;
1	2	login	user	2	\N	\N	\N	2026-02-18 13:07:15.211801
2	2	logout	user	2	\N	\N	\N	2026-02-18 13:07:15.214922
3	2	login	user	2	\N	\N	\N	2026-02-18 13:26:22.310078
4	2	login	user	2	\N	\N	\N	2026-02-18 13:51:41.0103
5	2	login	user	2	\N	\N	\N	2026-02-18 13:52:17.209497
6	2	login	user	2	\N	\N	\N	2026-02-18 13:55:20.006168
7	2	login	user	2	\N	\N	\N	2026-02-18 14:01:24.512416
8	2	login	user	2	\N	\N	\N	2026-02-18 14:05:10.905183
9	2	login	user	2	\N	\N	\N	2026-02-18 14:05:20.847753
10	2	login	user	2	\N	\N	\N	2026-02-18 14:05:34.345673
11	2	login	user	2	\N	\N	\N	2026-02-18 14:11:51.127559
12	2	login	user	2	\N	\N	\N	2026-02-18 14:18:15.382835
13	2	login	user	2	\N	\N	\N	2026-02-18 14:21:34.767681
14	2	login	user	2	\N	\N	\N	2026-02-18 14:23:12.580252
15	2	login	user	2	\N	\N	\N	2026-02-18 14:25:25.519062
16	2	login	user	2	\N	\N	\N	2026-02-18 14:25:46.361984
17	2	login	user	2	\N	\N	\N	2026-02-18 14:29:06.308598
18	2	login	user	2	\N	\N	\N	2026-02-18 14:30:52.884639
19	2	login	user	2	\N	\N	\N	2026-02-18 14:33:35.479936
20	2	login	user	2	\N	\N	\N	2026-02-18 14:36:38.479799
21	2	login	user	2	\N	\N	\N	2026-02-18 14:38:22.243555
22	2	login	user	2	\N	\N	\N	2026-02-18 14:39:54.210397
23	2	login	user	2	\N	\N	\N	2026-02-18 14:46:50.188148
24	2	login	user	2	\N	\N	\N	2026-02-18 15:12:50.93756
25	\N	update_password	user	2	\N	{"password_changed": true}	\N	2026-02-18 15:15:37.1939
26	2	login	user	2	\N	\N	\N	2026-02-18 15:16:08.377737
27	2	login	user	2	\N	\N	\N	2026-02-19 00:20:54.302682
28	2	login	user	2	\N	\N	\N	2026-02-19 01:00:55.325919
29	2	login	user	2	\N	\N	\N	2026-02-19 01:22:08.996877
30	2	login	user	2	\N	\N	\N	2026-02-19 01:24:43.849039
31	2	login	user	2	\N	\N	\N	2026-02-19 01:26:55.49407
32	2	login	user	2	\N	\N	\N	2026-02-19 01:33:01.94967
33	2	login	user	2	\N	\N	\N	2026-02-19 01:38:38.980433
34	2	login	user	2	\N	\N	\N	2026-02-19 01:47:36.837182
35	2	login	user	2	\N	\N	\N	2026-02-19 02:14:50.670301
36	2	login	user	2	\N	\N	\N	2026-02-19 02:28:30.33694
37	2	login	user	2	\N	\N	\N	2026-02-19 02:32:30.568116
38	2	login	user	2	\N	\N	\N	2026-02-19 02:43:07.756307
39	2	login	user	2	\N	\N	\N	2026-02-19 02:45:22.095741
40	2	login	user	2	\N	\N	\N	2026-02-19 02:55:59.571047
41	2	login	user	2	\N	\N	\N	2026-02-19 03:01:27.561921
42	2	login	user	2	\N	\N	\N	2026-02-19 03:04:31.273581
43	2	login	user	2	\N	\N	\N	2026-02-19 03:06:34.548463
44	2	login	user	2	\N	\N	\N	2026-02-19 03:18:25.983178
45	2	login	user	2	\N	\N	\N	2026-02-19 03:59:15.902871
46	2	login	user	2	\N	\N	\N	2026-02-19 04:04:54.872017
47	2	login	user	2	\N	\N	\N	2026-02-19 04:07:23.408428
48	2	login	user	2	\N	\N	\N	2026-02-19 04:08:33.34583
49	2	login	user	2	\N	\N	\N	2026-02-19 04:21:06.693594
50	2	login	user	2	\N	\N	\N	2026-02-19 04:34:03.147852
51	2	login	user	2	\N	\N	\N	2026-02-19 04:44:39.823725
52	2	login	user	2	\N	\N	\N	2026-02-19 04:46:18.001003
53	2	login	user	2	\N	\N	\N	2026-02-19 04:48:33.376759
54	2	login	user	2	\N	\N	\N	2026-02-19 04:54:23.535397
55	2	login	user	2	\N	\N	\N	2026-02-19 05:45:54.098272
56	2	login	user	2	\N	\N	\N	2026-02-19 05:52:45.613732
57	2	login	user	2	\N	\N	\N	2026-02-19 05:54:35.318274
58	2	login	user	2	\N	\N	\N	2026-02-19 05:55:49.902574
59	2	login	user	2	\N	\N	\N	2026-02-19 05:57:33.799562
60	2	login	user	2	\N	\N	\N	2026-02-19 06:05:29.943117
61	2	login	user	2	\N	\N	\N	2026-02-19 06:07:24.216254
62	2	login	user	2	\N	\N	\N	2026-02-19 06:09:46.275041
63	2	login	user	2	\N	\N	\N	2026-02-19 06:20:04.033873
64	2	login	user	2	\N	\N	\N	2026-02-19 06:36:44.158103
65	2	login	user	2	\N	\N	\N	2026-02-19 06:42:48.090477
66	2	login	user	2	\N	\N	\N	2026-02-19 06:45:26.182277
67	2	login	user	2	\N	\N	\N	2026-02-19 06:46:04.395413
68	2	login	user	2	\N	\N	\N	2026-02-19 06:47:29.743642
69	2	logout	user	2	\N	\N	\N	2026-02-19 06:48:03.365406
70	2	login	user	2	\N	\N	\N	2026-02-19 06:48:22.116622
71	2	login	user	2	\N	\N	\N	2026-02-19 07:16:55.593824
72	2	login	user	2	\N	\N	\N	2026-02-19 07:18:32.645201
73	2	login	user	2	\N	\N	\N	2026-02-19 07:20:25.027985
74	2	login	user	2	\N	\N	\N	2026-02-19 07:26:12.016853
75	2	login	user	2	\N	\N	\N	2026-02-19 07:33:17.912688
76	2	login	user	2	\N	\N	\N	2026-02-19 07:38:10.682231
77	2	login	user	2	\N	\N	\N	2026-02-19 08:18:59.715489
78	2	login	user	2	\N	\N	\N	2026-02-19 08:22:39.649183
79	2	login	user	2	\N	\N	\N	2026-02-19 08:27:00.854952
80	2	login	user	2	\N	\N	\N	2026-02-19 08:29:02.572821
81	2	login	user	2	\N	\N	\N	2026-02-19 08:33:19.035263
82	2	login	user	2	\N	\N	\N	2026-02-19 08:36:44.935144
83	2	login	user	2	\N	\N	\N	2026-02-19 08:41:29.620561
84	2	login	user	2	\N	\N	\N	2026-02-19 08:45:01.28689
85	2	login	user	2	\N	\N	\N	2026-02-19 08:47:17.961824
86	2	login	user	2	\N	\N	\N	2026-02-19 08:49:35.092802
87	2	login	user	2	\N	\N	\N	2026-02-19 08:52:26.89292
88	2	login	user	2	\N	\N	\N	2026-02-19 08:56:11.001108
89	2	login	user	2	\N	\N	\N	2026-02-19 08:57:46.177169
90	2	login	user	2	\N	\N	\N	2026-02-19 09:00:12.677285
91	2	login	user	2	\N	\N	\N	2026-02-19 09:00:36.634196
92	2	login	user	2	\N	\N	\N	2026-02-20 00:47:57.964248
93	2	login	user	2	\N	\N	\N	2026-02-20 00:49:09.144282
94	2	login	user	2	\N	\N	\N	2026-02-20 00:50:52.200558
95	2	login	user	2	\N	\N	\N	2026-02-20 00:54:51.264733
96	2	login	user	2	\N	\N	\N	2026-02-20 00:57:19.672898
97	2	login	user	2	\N	\N	\N	2026-02-20 01:06:44.176061
98	2	login	user	2	\N	\N	\N	2026-02-20 01:12:23.123438
99	2	login	user	2	\N	\N	\N	2026-02-20 01:12:43.023089
100	2	login	user	2	\N	\N	\N	2026-02-20 01:14:28.216716
101	2	login	user	2	\N	\N	\N	2026-02-20 01:16:04.354073
102	\N	update_password	user	2	\N	{"password_changed": true}	\N	2026-02-20 01:18:21.456483
103	2	login	user	2	\N	\N	\N	2026-02-20 01:18:43.541132
104	2	login	user	2	\N	\N	\N	2026-02-20 01:23:14.75354
105	2	login	user	2	\N	\N	\N	2026-02-20 01:28:49.354034
106	2	login	user	2	\N	\N	\N	2026-02-20 01:32:29.415073
107	2	login	user	2	\N	\N	\N	2026-02-20 01:37:23.072731
108	2	login	user	2	\N	\N	\N	2026-02-20 01:39:53.284857
109	2	login	user	2	\N	\N	\N	2026-02-20 01:40:46.970281
110	2	login	user	2	\N	\N	\N	2026-02-20 01:42:13.843734
111	2	login	user	2	\N	\N	\N	2026-02-20 01:43:19.359707
112	2	login	user	2	\N	\N	\N	2026-02-20 01:45:05.703798
113	2	login	user	2	\N	\N	\N	2026-02-20 01:47:45.921547
114	2	login	user	2	\N	\N	\N	2026-02-20 01:49:17.183946
115	2	login	user	2	\N	\N	\N	2026-02-20 01:52:59.969618
116	2	login	user	2	\N	\N	\N	2026-02-20 01:59:05.813758
117	2	login	user	2	\N	\N	\N	2026-02-20 02:07:17.828553
118	2	login	user	2	\N	\N	\N	2026-02-20 05:02:26.163778
119	2	login	user	2	\N	\N	\N	2026-02-20 05:11:54.724749
120	2	login	user	2	\N	\N	\N	2026-02-20 05:14:13.01046
121	2	login	user	2	\N	\N	\N	2026-02-20 05:25:52.349023
122	2	login	user	2	\N	\N	\N	2026-02-20 05:27:11.01545
123	2	login	user	2	\N	\N	\N	2026-02-20 05:36:34.798317
124	2	login	user	2	\N	\N	\N	2026-02-20 05:38:44.320412
125	2	login	user	2	\N	\N	\N	2026-02-20 05:39:40.521842
126	2	login	user	2	\N	\N	\N	2026-02-20 05:46:21.614429
127	2	login	user	2	\N	\N	\N	2026-02-20 05:49:59.571668
128	2	login	user	2	\N	\N	\N	2026-02-20 05:53:23.807782
129	2	login	user	2	\N	\N	\N	2026-02-20 05:55:48.496892
130	2	login	user	2	\N	\N	\N	2026-02-20 06:07:57.216536
131	2	login	user	2	\N	\N	\N	2026-02-20 06:11:35.348239
132	2	login	user	2	\N	\N	\N	2026-02-20 06:16:30.785669
133	2	login	user	2	\N	\N	\N	2026-02-20 06:16:54.048984
134	2	login	user	2	\N	\N	\N	2026-02-20 06:19:44.942581
135	2	login	user	2	\N	\N	\N	2026-02-20 06:22:56.835961
136	2	login	user	2	\N	\N	\N	2026-02-20 06:31:28.012324
137	2	login	user	2	\N	\N	\N	2026-02-20 06:33:52.184758
138	2	login	user	2	\N	\N	\N	2026-02-20 06:42:41.002454
139	2	login	user	2	\N	\N	\N	2026-02-20 06:45:11.593416
140	2	logout	user	2	\N	\N	\N	2026-02-20 06:46:59.879811
141	2	login	user	2	\N	\N	\N	2026-02-20 06:48:47.965301
142	2	login	user	2	\N	\N	\N	2026-02-20 07:13:45.286085
143	2	login	user	2	\N	\N	\N	2026-02-20 07:20:25.537082
144	2	login	user	2	\N	\N	\N	2026-02-20 13:19:18.001965
145	2	login	user	2	\N	\N	\N	2026-02-20 13:30:12.6446
146	2	login	user	2	\N	\N	\N	2026-02-20 13:38:02.84469
147	2	login	user	2	\N	\N	\N	2026-02-20 13:44:48.402342
148	2	login	user	2	\N	\N	\N	2026-02-20 13:59:14.362055
149	2	login	user	2	\N	\N	\N	2026-02-20 14:03:43.554825
150	2	login	user	2	\N	\N	\N	2026-02-20 14:06:27.385495
151	2	login	user	2	\N	\N	\N	2026-02-20 14:11:46.836924
152	2	login	user	2	\N	\N	\N	2026-02-20 14:23:56.72806
153	2	login	user	2	\N	\N	\N	2026-02-20 14:45:04.138559
154	2	login	user	2	\N	\N	\N	2026-02-20 14:51:05.449179
155	2	login	user	2	\N	\N	\N	2026-02-20 15:08:40.209126
156	2	login	user	2	\N	\N	\N	2026-02-20 15:15:02.464796
157	2	login	user	2	\N	\N	\N	2026-02-20 15:42:11.380758
158	2	login	user	2	\N	\N	\N	2026-02-20 16:09:09.738505
159	2	login	user	2	\N	\N	\N	2026-02-20 16:13:09.183614
160	2	login	user	2	\N	\N	\N	2026-02-20 16:15:36.188077
161	2	login	user	2	\N	\N	\N	2026-02-21 11:09:25.727242
162	2	login	user	2	\N	\N	\N	2026-02-21 11:31:18.407869
163	2	login	user	2	\N	\N	\N	2026-02-21 11:33:06.8187
164	2	login	user	2	\N	\N	\N	2026-02-21 11:35:03.867643
165	2	login	user	2	\N	\N	\N	2026-02-21 11:42:50.206243
166	2	login	user	2	\N	\N	\N	2026-02-21 11:49:09.477331
167	2	login	user	2	\N	\N	\N	2026-02-21 11:57:25.616266
168	2	login	user	2	\N	\N	\N	2026-02-21 12:04:23.008593
169	2	login	user	2	\N	\N	\N	2026-02-21 12:12:03.013915
170	2	login	user	2	\N	\N	\N	2026-02-21 12:14:26.900462
171	2	login	user	2	\N	\N	\N	2026-02-21 12:26:31.395287
172	2	login	user	2	\N	\N	\N	2026-02-21 12:29:09.276187
173	2	login	user	2	\N	\N	\N	2026-02-21 12:33:34.626521
174	2	login	user	2	\N	\N	\N	2026-02-21 12:44:37.047681
175	2	login	user	2	\N	\N	\N	2026-02-21 12:51:55.91254
176	2	login	user	2	\N	\N	\N	2026-02-21 12:56:59.494729
177	2	login	user	2	\N	\N	\N	2026-02-21 13:02:50.207825
178	2	login	user	2	\N	\N	\N	2026-02-21 13:06:20.636623
179	2	login	user	2	\N	\N	\N	2026-02-21 13:16:08.618589
180	2	login	user	2	\N	\N	\N	2026-02-22 03:11:27.998512
181	2	login	user	2	\N	\N	\N	2026-02-22 09:03:33.964247
182	2	login	user	2	\N	\N	\N	2026-02-22 09:52:05.969377
183	2	login	user	2	\N	\N	\N	2026-02-22 09:58:12.532353
184	2	login	user	2	\N	\N	\N	2026-02-23 03:58:41.349715
185	2	login	user	2	\N	\N	\N	2026-02-23 04:09:10.418131
186	2	login	user	2	\N	\N	\N	2026-02-23 04:22:19.683405
187	2	login	user	2	\N	\N	\N	2026-02-23 04:27:46.137768
188	2	login	user	2	\N	\N	\N	2026-02-23 04:31:03.762821
189	2	login	user	2	\N	\N	\N	2026-02-23 04:34:16.524544
190	2	login	user	2	\N	\N	\N	2026-02-23 04:38:26.063059
191	2	login	user	2	\N	\N	\N	2026-02-23 04:44:51.467501
192	2	login	user	2	\N	\N	\N	2026-02-23 04:53:33.546908
193	2	login	user	2	\N	\N	\N	2026-02-23 04:54:57.616769
194	2	login	user	2	\N	\N	\N	2026-02-23 05:29:40.349699
195	2	login	user	2	\N	\N	\N	2026-02-23 05:38:06.355724
196	2	login	user	2	\N	\N	\N	2026-02-23 05:42:03.686445
197	2	login	user	2	\N	\N	\N	2026-02-23 06:06:08.721247
198	2	login	user	2	\N	\N	\N	2026-02-23 06:10:10.095911
199	2	login	user	2	\N	\N	\N	2026-02-23 06:22:15.200884
200	2	login	user	2	\N	\N	\N	2026-02-23 13:22:21.369153
201	2	login	user	2	\N	\N	\N	2026-02-23 14:45:49.977284
202	2	login	user	2	\N	\N	\N	2026-02-23 14:58:53.065987
203	2	login	user	2	\N	\N	\N	2026-02-24 00:02:46.486734
204	2	login	user	2	\N	\N	\N	2026-02-24 00:20:15.587109
205	2	login	user	2	\N	\N	\N	2026-02-24 00:26:05.478596
206	2	login	user	2	\N	\N	\N	2026-02-24 00:36:45.00082
207	2	login	user	2	\N	\N	\N	2026-02-24 00:48:39.074188
208	2	login	user	2	\N	\N	\N	2026-02-24 00:52:34.205075
209	2	login	user	2	\N	\N	\N	2026-02-24 00:55:42.828859
210	2	login	user	2	\N	\N	\N	2026-02-24 00:57:54.062983
211	2	login	user	2	\N	\N	\N	2026-02-24 01:16:50.587449
212	2	login	user	2	\N	\N	\N	2026-02-24 02:47:44.972567
213	2	login	user	2	\N	\N	\N	2026-02-24 04:55:54.17562
214	2	login	user	2	\N	\N	\N	2026-02-24 05:02:42.427879
215	2	login	user	2	\N	\N	\N	2026-02-24 05:29:05.06879
216	2	logout	user	2	\N	\N	\N	2026-02-24 05:29:08.211092
217	\N	create_user	user	3	\N	{"role": "user", "username": "Неменущий Алексей"}	\N	2026-02-24 05:37:19.612391
218	2	login	user	2	\N	\N	\N	2026-02-24 06:11:16.995566
219	2	login	user	2	\N	\N	\N	2026-02-24 06:17:00.104062
220	2	login	user	2	\N	\N	\N	2026-02-24 07:00:28.313867
221	2	logout	user	2	\N	\N	\N	2026-02-24 07:03:06.840289
222	2	login	user	2	\N	\N	\N	2026-02-24 13:43:42.072936
223	\N	update_user_role	user	2	{"role": "admin"}	{"role": "admin"}	\N	2026-02-24 13:43:56.521023
224	\N	update_workstation	user	2	{"workstation": "Станок 1"}	{"workstation": null}	\N	2026-02-24 13:43:56.525184
225	2	login	user	2	\N	\N	\N	2026-02-25 00:31:41.599843
226	2	login	user	2	\N	\N	\N	2026-02-25 00:42:11.19465
227	2	login	user	2	\N	\N	\N	2026-02-25 00:50:11.321362
228	2	login	user	2	\N	\N	\N	2026-02-25 01:19:52.191288
229	2	login	user	2	\N	\N	\N	2026-02-25 02:26:11.208549
230	\N	update_user_role	user	3	\N	{"role": "user"}	\N	2026-02-25 02:27:21.272368
231	2	login	user	2	\N	\N	\N	2026-02-25 04:52:01.533464
232	2	login	user	2	\N	\N	\N	2026-02-25 04:55:33.67023
233	2	login	user	2	\N	\N	\N	2026-02-25 04:58:43.893894
234	2	login	user	2	\N	\N	\N	2026-02-25 05:51:24.772667
235	\N	delete_user	user	3	{"username": "Неменущий Алексей"}	\N	\N	2026-02-25 05:52:00.011052
236	2	login	user	2	\N	\N	\N	2026-02-25 08:09:14.517273
237	2	logout	user	2	\N	\N	\N	2026-02-25 08:09:30.058945
238	\N	create_user	user	5	\N	{"role": "user", "username": "Неменущий Алексей"}	\N	2026-02-25 08:15:29.182866
239	2	login	user	2	\N	\N	\N	2026-02-25 08:15:38.729302
240	2	logout	user	2	\N	\N	\N	2026-02-25 08:16:01.773275
1212	2	login	user	2	\N	\N	\N	2026-03-30 07:24:32.35506
242	2	login	user	2	\N	\N	\N	2026-02-26 00:20:44.303912
243	\N	update_workstation	user	5	{"workstation": "Верстак"}	{"workstation": null}	\N	2026-02-26 00:20:50.831858
244	2	login	user	2	\N	\N	\N	2026-02-26 00:29:21.906538
245	2	login	user	2	\N	\N	\N	2026-02-26 00:37:59.930197
246	2	login	user	2	\N	\N	\N	2026-02-26 00:43:18.829264
247	2	login	user	2	\N	\N	\N	2026-02-26 00:48:49.596793
248	2	login	user	2	\N	\N	\N	2026-02-26 00:59:02.664889
249	2	login	user	2	\N	\N	\N	2026-02-26 01:04:15.424763
250	2	login	user	2	\N	\N	\N	2026-02-26 01:13:33.760242
251	2	login	user	2	\N	\N	\N	2026-02-26 01:18:23.794417
252	2	login	user	2	\N	\N	\N	2026-02-26 01:27:15.010886
253	2	login	user	2	\N	\N	\N	2026-02-26 01:31:12.900547
254	2	login	user	2	\N	\N	\N	2026-02-26 01:34:36.803797
255	2	login	user	2	\N	\N	\N	2026-02-26 02:13:34.707165
256	2	login	user	2	\N	\N	\N	2026-02-26 02:22:15.817564
257	2	login	user	2	\N	\N	\N	2026-02-26 02:26:56.261539
258	2	login	user	2	\N	\N	\N	2026-02-26 02:59:13.459042
259	2	login	user	2	\N	\N	\N	2026-02-26 03:04:54.18312
260	2	login	user	2	\N	\N	\N	2026-02-26 03:06:36.4927
261	2	login	user	2	\N	\N	\N	2026-02-26 03:09:55.515378
262	2	login	user	2	\N	\N	\N	2026-02-26 03:20:40.210394
263	2	login	user	2	\N	\N	\N	2026-02-26 03:25:59.359179
264	2	login	user	2	\N	\N	\N	2026-02-26 03:29:24.146609
265	2	login	user	2	\N	\N	\N	2026-02-26 04:08:57.893692
266	2	login	user	2	\N	\N	\N	2026-02-26 04:21:14.563274
267	2	logout	user	2	\N	\N	\N	2026-02-26 04:23:21.707317
268	\N	create_user	user	6	\N	{"role": "user", "username": "Братушкин Роман"}	\N	2026-02-26 04:23:50.896792
1214	2	login	user	2	\N	\N	\N	2026-03-30 07:43:13.641839
1216	2	login	user	2	\N	\N	\N	2026-03-30 08:26:07.716235
271	\N	expense_item	item	900	{"quantity": 6}	{"quantity": 5}	\N	2026-02-26 04:46:31.800614
1218	2	login	user	2	\N	\N	\N	2026-03-30 08:52:31.772847
1220	2	login	user	2	\N	\N	\N	2026-03-31 00:33:38.477999
274	2	login	user	2	\N	\N	\N	2026-02-26 05:05:16.170959
1222	2	login	user	2	\N	\N	\N	2026-03-31 01:41:31.613682
1224	2	login	user	2	\N	\N	\N	2026-03-31 02:12:36.684311
277	\N	expense_item	item	901	{"quantity": 10}	{"quantity": 9}	\N	2026-02-26 06:29:06.173206
1226	2	login	user	2	\N	\N	\N	2026-03-31 03:09:24.529968
279	\N	expense_item	item	901	{"quantity": 9}	{"quantity": 8}	\N	2026-02-26 06:46:50.040037
1228	2	login	user	2	\N	\N	\N	2026-03-31 05:09:50.689424
281	\N	expense_item	item	900	{"quantity": 5}	{"quantity": 4}	\N	2026-02-26 06:49:42.168125
282	\N	expense_item	item	900	{"quantity": 4}	{"quantity": 3}	\N	2026-02-26 06:50:10.301332
283	2	login	user	2	\N	\N	\N	2026-02-26 06:50:47.352972
284	2	login	user	2	\N	\N	\N	2026-02-26 06:51:39.811291
285	2	login	user	2	\N	\N	\N	2026-02-26 07:04:18.818019
286	2	login	user	2	\N	\N	\N	2026-02-26 07:08:15.837189
287	\N	update_workstation	user	6	{"workstation": "Фрезерный IMU-5x400 - IMU-5x400-001"}	{"workstation": "Фрезерный IMU-5x400"}	\N	2026-02-26 07:09:25.492443
288	\N	update_workstation	user	6	{"workstation": "Фрезерный IMU-5x400"}	{"workstation": "Фрезерный IMU-5x400"}	\N	2026-02-26 07:09:36.684873
1230	2	login	user	2	\N	\N	\N	2026-03-31 07:26:57.802704
290	2	login	user	2	\N	\N	\N	2026-02-26 07:22:11.842802
291	2	login	user	2	\N	\N	\N	2026-02-26 07:31:59.987849
292	2	login	user	2	\N	\N	\N	2026-02-26 07:45:01.65333
293	2	login	user	2	\N	\N	\N	2026-02-26 07:51:31.178477
294	2	login	user	2	\N	\N	\N	2026-02-26 07:55:05.791788
295	2	login	user	2	\N	\N	\N	2026-02-26 08:01:50.745049
296	2	login	user	2	\N	\N	\N	2026-02-26 08:07:50.006274
297	2	login	user	2	\N	\N	\N	2026-02-27 00:51:29.474746
298	2	login	user	2	\N	\N	\N	2026-02-27 01:04:06.290353
299	2	login	user	2	\N	\N	\N	2026-02-27 01:16:52.453022
300	2	login	user	2	\N	\N	\N	2026-02-27 01:27:01.734461
301	2	login	user	2	\N	\N	\N	2026-02-27 01:31:30.473788
302	2	login	user	2	\N	\N	\N	2026-02-27 01:56:01.596455
303	2	login	user	2	\N	\N	\N	2026-02-27 02:00:03.891008
304	\N	update_workstation	user	6	{"workstation": "Фрезерный IMU-5x400"}	{"workstation": "Фрезерный IMU-5x400_№1"}	\N	2026-02-27 02:00:18.364978
305	\N	delete_user	user	6	{"username": "Братушкин Роман"}	\N	\N	2026-02-27 02:00:29.412334
306	2	login	user	2	\N	\N	\N	2026-02-27 02:05:41.892908
307	\N	delete_user	user	5	{"username": "Неменущий Алексей"}	\N	\N	2026-02-27 02:05:58.564563
308	2	login	user	2	\N	\N	\N	2026-02-27 02:49:38.753254
309	2	login	user	2	\N	\N	\N	2026-02-27 02:49:40.972679
310	2	login	user	2	\N	\N	\N	2026-02-27 02:49:53.636094
311	2	login	user	2	\N	\N	\N	2026-02-27 02:50:04.266866
312	2	login	user	2	\N	\N	\N	2026-02-27 02:56:14.190554
313	2	login	user	2	\N	\N	\N	2026-02-27 03:04:25.313936
314	2	login	user	2	\N	\N	\N	2026-02-27 03:04:33.567706
315	2	login	user	2	\N	\N	\N	2026-02-27 03:15:15.854146
316	2	logout	user	2	\N	\N	\N	2026-02-27 03:15:21.123933
317	2	login	user	2	\N	\N	\N	2026-02-27 05:08:53.324737
318	2	logout	user	2	\N	\N	\N	2026-02-27 05:08:58.333025
319	\N	create_user	user	7	\N	{"role": "user", "username": "Братушкин Роман"}	\N	2026-02-27 05:12:18.566204
321	2	login	user	2	\N	\N	\N	2026-02-27 05:12:51.892542
322	2	login	user	2	\N	\N	\N	2026-02-27 05:15:58.528808
323	2	login	user	2	\N	\N	\N	2026-02-27 05:19:07.625995
324	2	logout	user	2	\N	\N	\N	2026-02-27 05:19:20.311591
325	\N	create_user	user	8	\N	{"role": "user", "username": "Неменущий Алексей"}	\N	2026-02-27 05:19:58.834166
326	2	login	user	2	\N	\N	\N	2026-02-27 05:20:09.169291
327	\N	update_workstations	user	8	{"workstations": "[\\"\\\\u0412\\\\u0435\\\\u0440\\\\u0441\\\\u0442\\\\u0430\\\\u043a\\"]"}	{"workstations": null}	\N	2026-02-27 05:20:24.987467
328	2	login	user	2	\N	\N	\N	2026-02-27 05:51:36.422732
330	\N	expense_item	item	900	{"quantity": 3}	{"quantity": 2}	\N	2026-02-27 05:53:20.802394
450	2	login	user	2	\N	\N	\N	2026-03-05 00:49:56.968837
333	\N	income_item	item	900	{"quantity": 2}	{"quantity": 3}	\N	2026-02-27 06:30:36.096801
334	2	login	user	2	\N	\N	\N	2026-02-27 06:30:45.16534
335	2	login	user	2	\N	\N	\N	2026-02-27 06:54:51.451423
336	2	login	user	2	\N	\N	\N	2026-02-27 07:23:51.73381
338	\N	expense_item	item	901	{"quantity": 8}	{"quantity": 7}	\N	2026-02-27 07:32:38.791707
339	2	login	user	2	\N	\N	\N	2026-02-27 07:37:19.210596
340	2	login	user	2	\N	\N	\N	2026-02-28 10:50:17.887718
341	2	login	user	2	\N	\N	\N	2026-02-28 11:00:10.842958
342	2	login	user	2	\N	\N	\N	2026-02-28 11:02:05.365214
343	2	login	user	2	\N	\N	\N	2026-02-28 11:03:57.401215
344	2	login	user	2	\N	\N	\N	2026-02-28 11:12:24.739612
345	2	login	user	2	\N	\N	\N	2026-02-28 11:16:35.978761
346	2	login	user	2	\N	\N	\N	2026-02-28 11:25:02.893776
347	2	login	user	2	\N	\N	\N	2026-02-28 11:28:28.432747
348	2	login	user	2	\N	\N	\N	2026-02-28 11:35:10.989551
349	2	login	user	2	\N	\N	\N	2026-02-28 11:41:51.714616
350	2	login	user	2	\N	\N	\N	2026-02-28 11:46:06.363385
351	2	login	user	2	\N	\N	\N	2026-02-28 11:49:57.810265
352	2	login	user	2	\N	\N	\N	2026-02-28 12:03:25.293216
353	2	login	user	2	\N	\N	\N	2026-02-28 12:50:37.896701
354	2	login	user	2	\N	\N	\N	2026-02-28 12:55:26.207762
355	2	login	user	2	\N	\N	\N	2026-03-02 00:19:41.368332
356	2	login	user	2	\N	\N	\N	2026-03-02 00:29:39.716657
357	2	login	user	2	\N	\N	\N	2026-03-02 00:50:03.088601
358	2	login	user	2	\N	\N	\N	2026-03-02 01:10:05.255133
359	2	login	user	2	\N	\N	\N	2026-03-02 01:12:50.257988
360	2	login	user	2	\N	\N	\N	2026-03-02 01:13:55.486846
361	2	login	user	2	\N	\N	\N	2026-03-02 01:14:26.157301
362	2	login	user	2	\N	\N	\N	2026-03-02 01:21:07.638857
363	2	login	user	2	\N	\N	\N	2026-03-02 01:22:05.158346
364	2	login	user	2	\N	\N	\N	2026-03-02 01:28:58.801716
365	2	login	user	2	\N	\N	\N	2026-03-02 01:37:00.720674
366	2	login	user	2	\N	\N	\N	2026-03-02 01:47:04.65775
367	2	login	user	2	\N	\N	\N	2026-03-02 01:52:56.335674
368	2	login	user	2	\N	\N	\N	2026-03-02 01:58:22.173008
369	2	login	user	2	\N	\N	\N	2026-03-02 02:11:06.134958
370	2	login	user	2	\N	\N	\N	2026-03-02 02:20:15.246111
371	2	login	user	2	\N	\N	\N	2026-03-02 02:30:18.631608
372	2	login	user	2	\N	\N	\N	2026-03-02 02:43:29.460624
373	2	login	user	2	\N	\N	\N	2026-03-02 03:04:45.327323
374	2	login	user	2	\N	\N	\N	2026-03-02 04:42:34.229015
375	2	login	user	2	\N	\N	\N	2026-03-02 04:53:55.498911
376	2	login	user	2	\N	\N	\N	2026-03-02 04:55:29.83524
377	2	login	user	2	\N	\N	\N	2026-03-02 05:05:45.512151
378	2	login	user	2	\N	\N	\N	2026-03-02 05:20:30.595
379	2	login	user	2	\N	\N	\N	2026-03-02 05:27:09.774436
380	2	login	user	2	\N	\N	\N	2026-03-02 05:54:55.312869
381	2	login	user	2	\N	\N	\N	2026-03-02 06:06:45.932631
382	2	login	user	2	\N	\N	\N	2026-03-02 06:17:11.117869
383	2	login	user	2	\N	\N	\N	2026-03-02 06:24:14.23255
384	2	login	user	2	\N	\N	\N	2026-03-02 06:26:05.899225
385	2	login	user	2	\N	\N	\N	2026-03-02 06:34:01.712851
386	2	login	user	2	\N	\N	\N	2026-03-02 06:44:51.587979
387	2	login	user	2	\N	\N	\N	2026-03-02 06:52:42.168141
388	2	login	user	2	\N	\N	\N	2026-03-02 07:00:28.028905
389	2	login	user	2	\N	\N	\N	2026-03-02 07:08:13.069478
390	2	login	user	2	\N	\N	\N	2026-03-02 07:15:23.700482
391	2	login	user	2	\N	\N	\N	2026-03-02 07:28:27.8463
392	2	login	user	2	\N	\N	\N	2026-03-02 07:33:05.153391
393	2	login	user	2	\N	\N	\N	2026-03-02 07:35:52.820123
394	2	login	user	2	\N	\N	\N	2026-03-02 07:45:50.139154
395	2	login	user	2	\N	\N	\N	2026-03-02 07:53:40.695185
396	2	login	user	2	\N	\N	\N	2026-03-02 08:08:01.988563
397	2	login	user	2	\N	\N	\N	2026-03-02 08:23:59.895983
398	2	login	user	2	\N	\N	\N	2026-03-02 08:26:32.751292
399	2	login	user	2	\N	\N	\N	2026-03-02 08:29:11.795882
400	2	login	user	2	\N	\N	\N	2026-03-02 08:35:16.515258
401	2	login	user	2	\N	\N	\N	2026-03-02 08:41:42.188873
402	2	login	user	2	\N	\N	\N	2026-03-02 08:48:43.529433
403	2	login	user	2	\N	\N	\N	2026-03-02 08:51:19.690601
404	2	login	user	2	\N	\N	\N	2026-03-02 12:31:21.970956
405	2	login	user	2	\N	\N	\N	2026-03-02 12:54:18.64574
406	2	login	user	2	\N	\N	\N	2026-03-02 12:58:43.41832
407	2	login	user	2	\N	\N	\N	2026-03-02 13:01:52.153039
408	2	login	user	2	\N	\N	\N	2026-03-02 13:05:29.02088
409	2	login	user	2	\N	\N	\N	2026-03-02 13:09:18.244763
410	2	login	user	2	\N	\N	\N	2026-03-02 13:11:44.607578
411	2	login	user	2	\N	\N	\N	2026-03-03 00:02:41.853548
412	2	login	user	2	\N	\N	\N	2026-03-03 00:05:53.960282
413	2	login	user	2	\N	\N	\N	2026-03-03 00:26:36.587836
414	2	login	user	2	\N	\N	\N	2026-03-03 00:28:41.194802
415	2	login	user	2	\N	\N	\N	2026-03-03 00:54:01.758785
416	2	login	user	2	\N	\N	\N	2026-03-03 00:58:06.785596
417	2	login	user	2	\N	\N	\N	2026-03-03 01:23:54.590392
418	2	login	user	2	\N	\N	\N	2026-03-03 01:36:35.495254
419	2	login	user	2	\N	\N	\N	2026-03-03 01:40:29.61931
420	2	login	user	2	\N	\N	\N	2026-03-03 02:02:03.306001
421	2	login	user	2	\N	\N	\N	2026-03-03 02:10:31.544317
422	2	login	user	2	\N	\N	\N	2026-03-03 02:14:59.308669
423	2	login	user	2	\N	\N	\N	2026-03-03 02:27:01.114315
424	2	login	user	2	\N	\N	\N	2026-03-03 02:32:28.060122
425	2	login	user	2	\N	\N	\N	2026-03-03 02:41:54.31345
426	2	login	user	2	\N	\N	\N	2026-03-03 03:08:00.420369
427	2	login	user	2	\N	\N	\N	2026-03-03 03:20:01.482241
428	2	login	user	2	\N	\N	\N	2026-03-03 03:50:48.0714
429	2	login	user	2	\N	\N	\N	2026-03-03 03:57:17.768174
430	2	login	user	2	\N	\N	\N	2026-03-03 04:12:42.389642
431	2	login	user	2	\N	\N	\N	2026-03-03 04:28:58.73842
432	2	login	user	2	\N	\N	\N	2026-03-03 04:30:22.654647
433	2	login	user	2	\N	\N	\N	2026-03-03 04:51:18.907154
434	2	login	user	2	\N	\N	\N	2026-03-03 04:55:20.146214
435	2	login	user	2	\N	\N	\N	2026-03-03 04:56:20.346144
436	2	login	user	2	\N	\N	\N	2026-03-03 05:45:28.870231
437	2	login	user	2	\N	\N	\N	2026-03-03 08:09:36.587696
438	2	login	user	2	\N	\N	\N	2026-03-04 01:11:22.897731
439	2	login	user	2	\N	\N	\N	2026-03-04 02:50:34.904084
440	2	login	user	2	\N	\N	\N	2026-03-04 03:09:04.04834
441	2	login	user	2	\N	\N	\N	2026-03-04 03:58:44.625534
447	\N	income_item	item	901	{"quantity": 7}	{"quantity": 8}	\N	2026-03-04 07:44:35.454586
448	2	login	user	2	\N	\N	\N	2026-03-04 08:15:14.113621
451	2	login	user	2	\N	\N	\N	2026-03-05 02:51:36.132114
452	2	login	user	2	\N	\N	\N	2026-03-05 03:19:01.714314
453	2	login	user	2	\N	\N	\N	2026-03-05 03:23:31.262709
454	2	login	user	2	\N	\N	\N	2026-03-05 03:42:09.040479
455	2	login	user	2	\N	\N	\N	2026-03-05 03:45:18.697042
456	2	login	user	2	\N	\N	\N	2026-03-05 03:55:20.806729
457	2	login	user	2	\N	\N	\N	2026-03-05 03:59:17.865298
458	2	login	user	2	\N	\N	\N	2026-03-05 04:27:59.477206
459	2	login	user	2	\N	\N	\N	2026-03-05 04:32:18.334812
460	2	login	user	2	\N	\N	\N	2026-03-05 04:57:33.079238
461	2	login	user	2	\N	\N	\N	2026-03-05 05:08:53.532766
462	2	login	user	2	\N	\N	\N	2026-03-05 05:20:51.779334
463	2	login	user	2	\N	\N	\N	2026-03-05 05:30:59.846496
464	2	login	user	2	\N	\N	\N	2026-03-05 05:35:53.998068
465	2	login	user	2	\N	\N	\N	2026-03-05 05:45:23.748596
466	2	login	user	2	\N	\N	\N	2026-03-05 06:07:19.487137
467	2	login	user	2	\N	\N	\N	2026-03-05 06:12:07.555495
468	2	login	user	2	\N	\N	\N	2026-03-05 06:14:25.023174
469	2	login	user	2	\N	\N	\N	2026-03-05 06:18:32.39285
470	2	login	user	2	\N	\N	\N	2026-03-05 06:23:35.103914
471	2	login	user	2	\N	\N	\N	2026-03-05 06:30:28.282203
472	2	login	user	2	\N	\N	\N	2026-03-05 06:40:19.692919
473	2	login	user	2	\N	\N	\N	2026-03-05 06:47:03.32587
474	2	login	user	2	\N	\N	\N	2026-03-05 06:49:20.717723
475	2	login	user	2	\N	\N	\N	2026-03-05 06:50:54.131717
476	2	login	user	2	\N	\N	\N	2026-03-05 07:07:46.910559
477	2	login	user	2	\N	\N	\N	2026-03-05 07:44:23.20549
478	2	login	user	2	\N	\N	\N	2026-03-05 07:58:11.596202
479	2	login	user	2	\N	\N	\N	2026-03-05 08:17:52.518551
480	2	login	user	2	\N	\N	\N	2026-03-05 08:25:53.732966
481	2	login	user	2	\N	\N	\N	2026-03-05 08:35:21.77553
482	2	login	user	2	\N	\N	\N	2026-03-05 08:47:17.454966
483	2	login	user	2	\N	\N	\N	2026-03-05 08:51:09.380473
484	2	login	user	2	\N	\N	\N	2026-03-06 00:06:59.945026
485	2	login	user	2	\N	\N	\N	2026-03-06 00:16:19.534907
486	2	login	user	2	\N	\N	\N	2026-03-06 00:21:28.982943
487	2	login	user	2	\N	\N	\N	2026-03-06 00:33:30.954378
488	2	login	user	2	\N	\N	\N	2026-03-06 00:40:34.445901
489	2	login	user	2	\N	\N	\N	2026-03-06 00:49:42.870181
490	2	login	user	2	\N	\N	\N	2026-03-06 01:14:32.214215
491	2	login	user	2	\N	\N	\N	2026-03-06 01:24:07.065705
492	2	login	user	2	\N	\N	\N	2026-03-06 01:25:49.177734
493	2	login	user	2	\N	\N	\N	2026-03-06 01:43:41.064365
494	2	login	user	2	\N	\N	\N	2026-03-06 01:50:02.329147
495	2	login	user	2	\N	\N	\N	2026-03-06 01:53:32.69682
496	2	login	user	2	\N	\N	\N	2026-03-06 02:48:59.804605
497	2	login	user	2	\N	\N	\N	2026-03-06 03:04:05.801411
498	2	login	user	2	\N	\N	\N	2026-03-06 03:11:56.817859
499	2	login	user	2	\N	\N	\N	2026-03-06 03:19:26.609924
500	2	login	user	2	\N	\N	\N	2026-03-06 03:39:18.023659
501	2	login	user	2	\N	\N	\N	2026-03-06 04:32:33.656045
502	2	login	user	2	\N	\N	\N	2026-03-06 04:40:44.432535
503	2	login	user	2	\N	\N	\N	2026-03-06 04:58:57.00432
504	2	login	user	2	\N	\N	\N	2026-03-06 05:10:40.322495
505	2	login	user	2	\N	\N	\N	2026-03-06 05:18:50.883447
506	2	login	user	2	\N	\N	\N	2026-03-06 05:22:28.42602
507	2	login	user	2	\N	\N	\N	2026-03-06 05:25:29.311427
508	2	login	user	2	\N	\N	\N	2026-03-06 05:26:40.791549
509	2	login	user	2	\N	\N	\N	2026-03-06 05:30:20.48139
510	2	login	user	2	\N	\N	\N	2026-03-06 05:52:24.814109
511	2	login	user	2	\N	\N	\N	2026-03-06 06:01:01.934858
512	2	login	user	2	\N	\N	\N	2026-03-06 06:07:25.780946
513	\N	update_workstations	user	8	{"workstations": null}	{"workstations": null}	\N	2026-03-06 06:08:11.546981
514	8	login	user	8	\N	\N	\N	2026-03-06 06:08:24.81651
515	2	login	user	2	\N	\N	\N	2026-03-06 06:11:40.554668
516	8	login	user	8	\N	\N	\N	2026-03-06 06:11:52.755276
517	2	login	user	2	\N	\N	\N	2026-03-06 06:24:47.592639
518	2	login	user	2	\N	\N	\N	2026-03-06 06:29:06.576059
519	2	login	user	2	\N	\N	\N	2026-03-06 06:54:53.473911
520	2	login	user	2	\N	\N	\N	2026-03-06 07:03:56.33925
521	2	login	user	2	\N	\N	\N	2026-03-06 07:08:36.501031
522	2	login	user	2	\N	\N	\N	2026-03-06 07:12:01.932562
523	2	login	user	2	\N	\N	\N	2026-03-06 07:15:37.597882
524	2	login	user	2	\N	\N	\N	2026-03-06 07:27:06.670757
525	2	login	user	2	\N	\N	\N	2026-03-06 07:42:12.288258
526	2	login	user	2	\N	\N	\N	2026-03-06 07:51:35.617726
527	2	login	user	2	\N	\N	\N	2026-03-06 08:12:57.889983
528	2	login	user	2	\N	\N	\N	2026-03-06 08:21:20.702074
529	2	login	user	2	\N	\N	\N	2026-03-06 08:22:32.822449
530	2	login	user	2	\N	\N	\N	2026-03-06 08:23:17.822018
531	2	login	user	2	\N	\N	\N	2026-03-06 08:33:13.890017
532	2	login	user	2	\N	\N	\N	2026-03-06 08:36:13.570692
533	2	login	user	2	\N	\N	\N	2026-03-06 08:40:13.312808
534	2	login	user	2	\N	\N	\N	2026-03-06 08:45:35.30728
535	2	login	user	2	\N	\N	\N	2026-03-06 08:50:15.163186
536	2	login	user	2	\N	\N	\N	2026-03-06 09:00:01.442778
537	2	login	user	2	\N	\N	\N	2026-03-07 09:01:37.324915
538	2	login	user	2	\N	\N	\N	2026-03-07 09:08:25.530208
539	2	login	user	2	\N	\N	\N	2026-03-07 09:11:28.708473
540	2	login	user	2	\N	\N	\N	2026-03-07 09:38:04.106007
541	2	login	user	2	\N	\N	\N	2026-03-07 09:45:25.985352
542	2	login	user	2	\N	\N	\N	2026-03-07 09:47:54.421753
543	2	login	user	2	\N	\N	\N	2026-03-07 09:51:48.253004
544	2	login	user	2	\N	\N	\N	2026-03-07 10:20:09.347026
545	2	login	user	2	\N	\N	\N	2026-03-07 10:22:12.013304
546	2	login	user	2	\N	\N	\N	2026-03-07 10:24:00.06897
547	2	login	user	2	\N	\N	\N	2026-03-07 10:35:46.883993
548	2	login	user	2	\N	\N	\N	2026-03-07 10:38:07.882441
549	2	login	user	2	\N	\N	\N	2026-03-07 10:56:47.107666
550	2	login	user	2	\N	\N	\N	2026-03-07 11:08:46.05116
551	2	login	user	2	\N	\N	\N	2026-03-07 16:26:51.308193
552	2	login	user	2	\N	\N	\N	2026-03-07 16:33:47.719019
553	2	login	user	2	\N	\N	\N	2026-03-07 16:36:28.093112
554	2	login	user	2	\N	\N	\N	2026-03-07 16:38:55.357882
555	2	login	user	2	\N	\N	\N	2026-03-07 16:40:47.521675
556	2	login	user	2	\N	\N	\N	2026-03-07 16:44:24.468308
557	2	login	user	2	\N	\N	\N	2026-03-07 16:47:20.739426
558	2	login	user	2	\N	\N	\N	2026-03-07 16:50:39.624995
559	2	login	user	2	\N	\N	\N	2026-03-07 16:53:02.428931
560	2	login	user	2	\N	\N	\N	2026-03-08 02:13:02.911628
561	2	login	user	2	\N	\N	\N	2026-03-08 02:42:26.615906
562	2	login	user	2	\N	\N	\N	2026-03-08 02:51:58.555045
563	2	login	user	2	\N	\N	\N	2026-03-08 03:15:48.848463
564	2	login	user	2	\N	\N	\N	2026-03-08 03:23:26.158164
565	2	login	user	2	\N	\N	\N	2026-03-08 03:40:33.701522
566	2	login	user	2	\N	\N	\N	2026-03-08 03:44:13.679708
567	2	login	user	2	\N	\N	\N	2026-03-08 03:48:37.620681
568	2	login	user	2	\N	\N	\N	2026-03-08 03:50:45.579177
569	2	login	user	2	\N	\N	\N	2026-03-09 00:23:50.485663
570	2	login	user	2	\N	\N	\N	2026-03-09 00:27:45.333819
571	2	login	user	2	\N	\N	\N	2026-03-09 00:32:19.764064
572	2	login	user	2	\N	\N	\N	2026-03-09 00:35:45.466717
573	2	login	user	2	\N	\N	\N	2026-03-09 00:40:00.580735
574	2	login	user	2	\N	\N	\N	2026-03-09 01:50:43.02643
575	2	login	user	2	\N	\N	\N	2026-03-09 01:51:56.589688
576	2	login	user	2	\N	\N	\N	2026-03-09 01:56:23.049186
577	2	login	user	2	\N	\N	\N	2026-03-09 02:05:13.380578
578	2	login	user	2	\N	\N	\N	2026-03-09 02:11:43.001434
579	2	login	user	2	\N	\N	\N	2026-03-09 02:16:22.951214
580	2	login	user	2	\N	\N	\N	2026-03-09 02:18:05.325213
581	2	login	user	2	\N	\N	\N	2026-03-09 02:23:33.852589
582	2	login	user	2	\N	\N	\N	2026-03-09 02:25:04.90862
583	2	login	user	2	\N	\N	\N	2026-03-09 02:48:17.424511
584	2	login	user	2	\N	\N	\N	2026-03-09 02:49:20.012503
585	2	login	user	2	\N	\N	\N	2026-03-09 03:07:45.134241
586	2	login	user	2	\N	\N	\N	2026-03-09 03:12:21.013346
587	2	login	user	2	\N	\N	\N	2026-03-09 03:16:52.984542
588	2	login	user	2	\N	\N	\N	2026-03-09 03:19:49.553711
589	2	login	user	2	\N	\N	\N	2026-03-09 03:25:33.888571
590	2	login	user	2	\N	\N	\N	2026-03-09 03:29:13.276486
591	2	login	user	2	\N	\N	\N	2026-03-09 03:35:11.234876
592	2	login	user	2	\N	\N	\N	2026-03-09 03:40:07.030725
593	2	login	user	2	\N	\N	\N	2026-03-09 03:45:51.262009
594	2	login	user	2	\N	\N	\N	2026-03-09 03:48:06.535532
595	2	login	user	2	\N	\N	\N	2026-03-09 03:50:46.759992
596	2	login	user	2	\N	\N	\N	2026-03-09 03:55:45.825525
597	2	login	user	2	\N	\N	\N	2026-03-09 04:00:37.390094
598	2	login	user	2	\N	\N	\N	2026-03-09 04:02:55.149376
599	2	login	user	2	\N	\N	\N	2026-03-09 04:04:46.819496
600	2	login	user	2	\N	\N	\N	2026-03-09 04:07:05.718947
601	2	login	user	2	\N	\N	\N	2026-03-09 04:11:26.221234
602	2	login	user	2	\N	\N	\N	2026-03-09 04:13:16.239699
603	2	login	user	2	\N	\N	\N	2026-03-09 04:20:43.33166
604	2	login	user	2	\N	\N	\N	2026-03-09 04:27:12.235001
605	2	login	user	2	\N	\N	\N	2026-03-09 04:34:15.163761
606	2	login	user	2	\N	\N	\N	2026-03-09 04:37:15.76081
607	2	login	user	2	\N	\N	\N	2026-03-09 04:49:39.343886
608	2	login	user	2	\N	\N	\N	2026-03-09 04:56:55.75909
609	2	login	user	2	\N	\N	\N	2026-03-09 05:01:04.654328
610	2	login	user	2	\N	\N	\N	2026-03-09 05:03:38.206447
611	2	login	user	2	\N	\N	\N	2026-03-09 05:05:52.586653
612	2	login	user	2	\N	\N	\N	2026-03-09 05:17:42.748605
613	2	login	user	2	\N	\N	\N	2026-03-09 05:21:45.242913
614	2	login	user	2	\N	\N	\N	2026-03-09 05:27:06.570168
615	2	login	user	2	\N	\N	\N	2026-03-09 05:36:46.107796
616	2	login	user	2	\N	\N	\N	2026-03-09 05:42:55.28056
617	2	login	user	2	\N	\N	\N	2026-03-09 05:57:45.08286
618	2	login	user	2	\N	\N	\N	2026-03-09 06:00:52.144267
619	2	login	user	2	\N	\N	\N	2026-03-09 06:02:22.425116
620	2	login	user	2	\N	\N	\N	2026-03-09 06:05:11.396561
621	2	login	user	2	\N	\N	\N	2026-03-09 06:06:48.567271
622	2	login	user	2	\N	\N	\N	2026-03-09 06:14:51.084518
623	2	login	user	2	\N	\N	\N	2026-03-09 06:18:40.352437
624	2	login	user	2	\N	\N	\N	2026-03-09 06:19:47.605055
625	2	login	user	2	\N	\N	\N	2026-03-09 06:22:08.593007
626	2	login	user	2	\N	\N	\N	2026-03-09 06:25:51.689147
627	2	login	user	2	\N	\N	\N	2026-03-09 06:27:48.178727
628	2	login	user	2	\N	\N	\N	2026-03-09 08:13:37.062154
629	2	login	user	2	\N	\N	\N	2026-03-09 08:32:13.350314
630	2	login	user	2	\N	\N	\N	2026-03-09 08:57:02.968195
631	2	login	user	2	\N	\N	\N	2026-03-09 09:18:13.255018
632	2	login	user	2	\N	\N	\N	2026-03-09 09:31:52.510558
633	2	login	user	2	\N	\N	\N	2026-03-09 09:49:38.365783
634	2	login	user	2	\N	\N	\N	2026-03-09 10:42:25.209957
635	2	login	user	2	\N	\N	\N	2026-03-09 10:55:00.496296
636	2	login	user	2	\N	\N	\N	2026-03-09 10:57:42.628756
637	2	login	user	2	\N	\N	\N	2026-03-09 10:59:12.959598
638	2	login	user	2	\N	\N	\N	2026-03-09 11:03:04.249957
639	2	login	user	2	\N	\N	\N	2026-03-09 11:12:10.961721
640	2	login	user	2	\N	\N	\N	2026-03-09 12:33:30.178972
641	2	login	user	2	\N	\N	\N	2026-03-09 12:35:25.957748
642	2	login	user	2	\N	\N	\N	2026-03-09 12:45:23.573799
643	2	login	user	2	\N	\N	\N	2026-03-09 12:55:22.607842
644	2	login	user	2	\N	\N	\N	2026-03-09 13:04:45.17609
645	2	login	user	2	\N	\N	\N	2026-03-09 13:12:19.559544
646	2	login	user	2	\N	\N	\N	2026-03-09 13:28:53.813895
647	2	login	user	2	\N	\N	\N	2026-03-09 13:44:09.461148
648	2	login	user	2	\N	\N	\N	2026-03-09 14:30:22.8668
649	2	login	user	2	\N	\N	\N	2026-03-10 00:02:43.405182
650	2	login	user	2	\N	\N	\N	2026-03-10 00:29:28.883434
651	2	login	user	2	\N	\N	\N	2026-03-10 01:16:56.614915
652	2	login	user	2	\N	\N	\N	2026-03-10 05:38:14.849512
653	2	login	user	2	\N	\N	\N	2026-03-10 05:40:15.567736
654	2	login	user	2	\N	\N	\N	2026-03-10 05:55:34.071959
655	2	login	user	2	\N	\N	\N	2026-03-10 05:58:44.817405
656	2	login	user	2	\N	\N	\N	2026-03-10 06:09:49.617579
657	2	login	user	2	\N	\N	\N	2026-03-10 06:16:24.681854
658	2	login	user	2	\N	\N	\N	2026-03-10 06:20:39.875874
659	2	login	user	2	\N	\N	\N	2026-03-10 06:51:23.575687
660	2	login	user	2	\N	\N	\N	2026-03-10 07:32:17.550326
661	2	login	user	2	\N	\N	\N	2026-03-10 07:53:10.095721
662	2	login	user	2	\N	\N	\N	2026-03-11 05:59:51.069118
663	2	login	user	2	\N	\N	\N	2026-03-11 06:38:08.78631
664	2	login	user	2	\N	\N	\N	2026-03-11 06:39:31.109075
665	2	login	user	2	\N	\N	\N	2026-03-11 06:41:58.588736
666	2	login	user	2	\N	\N	\N	2026-03-11 06:43:15.95144
667	2	login	user	2	\N	\N	\N	2026-03-11 06:46:59.689907
668	2	login	user	2	\N	\N	\N	2026-03-11 06:48:48.631144
669	2	login	user	2	\N	\N	\N	2026-03-11 06:55:14.811466
670	2	login	user	2	\N	\N	\N	2026-03-11 06:57:35.229242
671	2	login	user	2	\N	\N	\N	2026-03-11 06:59:12.291045
672	2	login	user	2	\N	\N	\N	2026-03-11 07:17:05.134263
673	2	login	user	2	\N	\N	\N	2026-03-11 07:29:30.450521
674	2	login	user	2	\N	\N	\N	2026-03-11 07:42:31.429781
675	2	login	user	2	\N	\N	\N	2026-03-11 07:51:32.961482
676	2	login	user	2	\N	\N	\N	2026-03-11 08:00:44.323587
677	2	login	user	2	\N	\N	\N	2026-03-11 08:14:12.722367
678	2	login	user	2	\N	\N	\N	2026-03-11 08:17:13.525257
679	2	login	user	2	\N	\N	\N	2026-03-11 08:21:12.377051
680	2	login	user	2	\N	\N	\N	2026-03-11 08:23:42.733706
681	2	login	user	2	\N	\N	\N	2026-03-11 08:43:44.781776
682	2	login	user	2	\N	\N	\N	2026-03-11 08:51:07.49354
683	2	login	user	2	\N	\N	\N	2026-03-11 13:27:44.578679
684	2	login	user	2	\N	\N	\N	2026-03-11 13:32:49.068051
685	2	login	user	2	\N	\N	\N	2026-03-11 13:41:15.869499
686	2	login	user	2	\N	\N	\N	2026-03-11 13:53:35.629287
687	2	login	user	2	\N	\N	\N	2026-03-11 13:56:06.707606
688	2	login	user	2	\N	\N	\N	2026-03-11 13:57:13.029933
689	2	login	user	2	\N	\N	\N	2026-03-11 13:58:29.984691
690	2	login	user	2	\N	\N	\N	2026-03-11 14:00:07.430955
691	2	login	user	2	\N	\N	\N	2026-03-12 00:12:17.830985
692	2	login	user	2	\N	\N	\N	2026-03-12 00:18:42.117861
693	2	login	user	2	\N	\N	\N	2026-03-12 00:26:30.833939
694	2	login	user	2	\N	\N	\N	2026-03-12 00:32:01.799299
695	2	login	user	2	\N	\N	\N	2026-03-12 00:36:17.052555
696	2	login	user	2	\N	\N	\N	2026-03-12 00:59:34.302597
697	2	login	user	2	\N	\N	\N	2026-03-12 01:01:59.460552
698	2	login	user	2	\N	\N	\N	2026-03-12 01:13:45.087926
699	2	login	user	2	\N	\N	\N	2026-03-12 01:20:13.142663
700	2	login	user	2	\N	\N	\N	2026-03-12 02:04:48.827784
701	2	login	user	2	\N	\N	\N	2026-03-12 02:10:17.88559
702	2	login	user	2	\N	\N	\N	2026-03-12 02:15:24.967717
703	2	login	user	2	\N	\N	\N	2026-03-12 02:17:33.547891
704	2	login	user	2	\N	\N	\N	2026-03-12 02:25:37.826984
705	2	login	user	2	\N	\N	\N	2026-03-12 02:44:32.099353
706	2	login	user	2	\N	\N	\N	2026-03-12 02:55:28.570499
707	2	login	user	2	\N	\N	\N	2026-03-12 03:30:19.609369
708	2	login	user	2	\N	\N	\N	2026-03-12 03:39:24.177802
709	2	login	user	2	\N	\N	\N	2026-03-12 03:44:38.550038
710	2	login	user	2	\N	\N	\N	2026-03-12 03:49:07.782097
711	2	login	user	2	\N	\N	\N	2026-03-12 03:51:50.429451
712	2	login	user	2	\N	\N	\N	2026-03-12 04:02:59.724317
713	2	login	user	2	\N	\N	\N	2026-03-12 04:08:57.000795
714	2	login	user	2	\N	\N	\N	2026-03-12 04:28:46.204136
715	2	login	user	2	\N	\N	\N	2026-03-12 04:32:47.266625
716	2	login	user	2	\N	\N	\N	2026-03-12 04:40:31.644093
717	2	login	user	2	\N	\N	\N	2026-03-12 04:55:04.892313
718	2	login	user	2	\N	\N	\N	2026-03-12 06:08:11.6715
719	2	login	user	2	\N	\N	\N	2026-03-12 06:13:10.936353
720	2	login	user	2	\N	\N	\N	2026-03-12 06:22:33.730774
721	2	login	user	2	\N	\N	\N	2026-03-12 06:34:14.228196
722	2	login	user	2	\N	\N	\N	2026-03-12 06:44:06.705614
723	2	login	user	2	\N	\N	\N	2026-03-12 06:47:57.995487
724	2	login	user	2	\N	\N	\N	2026-03-12 06:50:46.04548
725	2	login	user	2	\N	\N	\N	2026-03-12 06:53:58.711385
726	2	login	user	2	\N	\N	\N	2026-03-12 06:57:58.756523
727	2	login	user	2	\N	\N	\N	2026-03-12 07:00:06.025767
728	2	login	user	2	\N	\N	\N	2026-03-12 07:09:43.345386
729	2	login	user	2	\N	\N	\N	2026-03-12 07:10:28.53245
730	2	login	user	2	\N	\N	\N	2026-03-12 07:13:29.559705
731	2	login	user	2	\N	\N	\N	2026-03-12 07:26:22.939616
732	2	login	user	2	\N	\N	\N	2026-03-12 07:33:31.371474
733	2	login	user	2	\N	\N	\N	2026-03-12 07:40:59.789159
734	2	login	user	2	\N	\N	\N	2026-03-12 08:24:28.122117
735	2	login	user	2	\N	\N	\N	2026-03-12 08:29:08.877452
736	2	login	user	2	\N	\N	\N	2026-03-12 08:35:55.689445
737	2	login	user	2	\N	\N	\N	2026-03-12 08:39:11.990761
738	2	login	user	2	\N	\N	\N	2026-03-12 08:50:03.82338
739	2	login	user	2	\N	\N	\N	2026-03-13 00:11:33.96411
740	2	login	user	2	\N	\N	\N	2026-03-13 00:27:24.905338
741	2	login	user	2	\N	\N	\N	2026-03-13 00:31:56.654462
742	2	login	user	2	\N	\N	\N	2026-03-13 00:36:12.576229
743	2	login	user	2	\N	\N	\N	2026-03-13 00:38:18.152031
744	2	login	user	2	\N	\N	\N	2026-03-13 00:43:06.581743
745	2	login	user	2	\N	\N	\N	2026-03-13 00:47:40.332672
746	2	login	user	2	\N	\N	\N	2026-03-13 00:50:17.563352
747	2	login	user	2	\N	\N	\N	2026-03-13 00:54:15.15055
748	2	login	user	2	\N	\N	\N	2026-03-13 01:03:51.681721
749	2	login	user	2	\N	\N	\N	2026-03-13 04:45:01.988428
750	2	login	user	2	\N	\N	\N	2026-03-13 04:49:28.309746
751	2	login	user	2	\N	\N	\N	2026-03-13 04:52:36.54943
752	2	login	user	2	\N	\N	\N	2026-03-13 05:00:31.750619
753	2	login	user	2	\N	\N	\N	2026-03-13 05:03:09.318864
754	2	login	user	2	\N	\N	\N	2026-03-13 05:08:25.563662
755	2	login	user	2	\N	\N	\N	2026-03-13 05:20:06.861685
756	2	login	user	2	\N	\N	\N	2026-03-13 05:22:47.757967
757	2	login	user	2	\N	\N	\N	2026-03-13 05:30:56.954858
758	2	login	user	2	\N	\N	\N	2026-03-13 05:34:53.670723
759	2	login	user	2	\N	\N	\N	2026-03-13 05:54:02.600321
760	2	login	user	2	\N	\N	\N	2026-03-13 06:11:22.223366
761	2	login	user	2	\N	\N	\N	2026-03-13 06:20:29.941745
762	2	login	user	2	\N	\N	\N	2026-03-13 06:35:48.693963
763	2	login	user	2	\N	\N	\N	2026-03-13 06:46:21.852449
764	2	login	user	2	\N	\N	\N	2026-03-13 06:53:02.384293
765	2	login	user	2	\N	\N	\N	2026-03-13 07:01:56.86704
766	2	login	user	2	\N	\N	\N	2026-03-13 07:12:55.688357
767	2	login	user	2	\N	\N	\N	2026-03-13 07:18:30.727529
768	2	login	user	2	\N	\N	\N	2026-03-13 07:21:15.494445
769	2	login	user	2	\N	\N	\N	2026-03-13 07:26:16.101192
770	2	login	user	2	\N	\N	\N	2026-03-13 07:40:27.97523
771	2	login	user	2	\N	\N	\N	2026-03-13 07:48:01.071317
772	2	login	user	2	\N	\N	\N	2026-03-13 07:51:44.781838
773	2	login	user	2	\N	\N	\N	2026-03-13 08:32:19.682564
774	2	login	user	2	\N	\N	\N	2026-03-13 08:34:28.283358
775	2	login	user	2	\N	\N	\N	2026-03-13 08:35:04.536423
776	2	login	user	2	\N	\N	\N	2026-03-13 08:43:15.881682
777	2	login	user	2	\N	\N	\N	2026-03-13 13:43:45.130421
778	2	login	user	2	\N	\N	\N	2026-03-13 13:47:23.756465
779	2	login	user	2	\N	\N	\N	2026-03-13 13:54:53.80816
780	2	login	user	2	\N	\N	\N	2026-03-13 13:56:48.634087
781	2	login	user	2	\N	\N	\N	2026-03-13 13:58:20.950966
782	2	login	user	2	\N	\N	\N	2026-03-13 14:00:17.280543
783	2	login	user	2	\N	\N	\N	2026-03-13 14:11:13.578696
784	2	login	user	2	\N	\N	\N	2026-03-13 14:13:55.231356
785	2	login	user	2	\N	\N	\N	2026-03-13 14:19:36.726687
786	2	login	user	2	\N	\N	\N	2026-03-13 14:47:28.522458
787	2	login	user	2	\N	\N	\N	2026-03-13 15:05:08.495087
788	2	login	user	2	\N	\N	\N	2026-03-13 15:10:11.557642
789	2	login	user	2	\N	\N	\N	2026-03-13 15:10:11.750333
790	2	login	user	2	\N	\N	\N	2026-03-13 15:13:00.331994
791	2	login	user	2	\N	\N	\N	2026-03-15 06:07:52.154982
792	2	login	user	2	\N	\N	\N	2026-03-15 06:09:50.193386
793	2	login	user	2	\N	\N	\N	2026-03-15 06:15:01.737915
794	2	login	user	2	\N	\N	\N	2026-03-15 06:18:51.584741
795	2	login	user	2	\N	\N	\N	2026-03-15 06:22:50.765834
796	2	login	user	2	\N	\N	\N	2026-03-15 06:24:57.023223
797	2	login	user	2	\N	\N	\N	2026-03-15 06:49:04.483135
798	2	login	user	2	\N	\N	\N	2026-03-15 06:53:21.569428
799	2	login	user	2	\N	\N	\N	2026-03-15 06:54:08.462025
800	2	login	user	2	\N	\N	\N	2026-03-15 07:16:37.517052
801	2	login	user	2	\N	\N	\N	2026-03-15 07:24:40.382595
802	2	login	user	2	\N	\N	\N	2026-03-15 07:40:30.307723
803	2	login	user	2	\N	\N	\N	2026-03-15 07:44:43.77254
804	2	login	user	2	\N	\N	\N	2026-03-15 07:54:05.450798
805	2	login	user	2	\N	\N	\N	2026-03-15 07:54:52.458234
806	2	login	user	2	\N	\N	\N	2026-03-15 07:58:35.876246
807	2	login	user	2	\N	\N	\N	2026-03-15 07:59:12.84756
808	2	login	user	2	\N	\N	\N	2026-03-15 08:40:57.241566
809	2	login	user	2	\N	\N	\N	2026-03-15 08:43:55.835577
810	2	login	user	2	\N	\N	\N	2026-03-15 08:45:48.913939
811	2	login	user	2	\N	\N	\N	2026-03-15 08:46:26.5011
812	2	login	user	2	\N	\N	\N	2026-03-15 08:52:27.102276
813	2	login	user	2	\N	\N	\N	2026-03-15 13:06:24.227116
814	2	login	user	2	\N	\N	\N	2026-03-15 13:07:51.79902
815	2	login	user	2	\N	\N	\N	2026-03-15 13:08:21.798974
816	2	login	user	2	\N	\N	\N	2026-03-15 13:18:36.189955
817	2	login	user	2	\N	\N	\N	2026-03-16 00:10:47.800132
818	2	login	user	2	\N	\N	\N	2026-03-16 00:16:07.39661
819	2	login	user	2	\N	\N	\N	2026-03-16 01:38:41.651585
820	2	login	user	2	\N	\N	\N	2026-03-16 01:45:50.103538
821	2	login	user	2	\N	\N	\N	2026-03-16 01:57:36.273513
822	2	login	user	2	\N	\N	\N	2026-03-16 02:12:30.532587
823	2	login	user	2	\N	\N	\N	2026-03-16 02:20:27.637119
824	2	login	user	2	\N	\N	\N	2026-03-16 02:38:16.671893
825	2	login	user	2	\N	\N	\N	2026-03-16 02:50:21.72468
826	2	login	user	2	\N	\N	\N	2026-03-16 02:52:15.477661
827	2	login	user	2	\N	\N	\N	2026-03-16 03:20:28.769347
828	2	login	user	2	\N	\N	\N	2026-03-16 03:50:18.201249
829	2	login	user	2	\N	\N	\N	2026-03-16 03:57:47.516458
830	2	login	user	2	\N	\N	\N	2026-03-16 04:03:57.917032
831	2	login	user	2	\N	\N	\N	2026-03-16 04:07:20.032687
832	2	login	user	2	\N	\N	\N	2026-03-16 04:15:07.220503
833	2	login	user	2	\N	\N	\N	2026-03-16 04:29:11.217113
834	2	login	user	2	\N	\N	\N	2026-03-16 04:33:49.454729
835	2	login	user	2	\N	\N	\N	2026-03-16 04:37:02.030086
836	2	login	user	2	\N	\N	\N	2026-03-16 04:41:24.152179
837	2	login	user	2	\N	\N	\N	2026-03-16 04:48:44.974048
838	2	login	user	2	\N	\N	\N	2026-03-16 04:57:00.892439
839	2	login	user	2	\N	\N	\N	2026-03-16 05:02:54.361991
840	2	login	user	2	\N	\N	\N	2026-03-16 05:07:16.629769
841	2	login	user	2	\N	\N	\N	2026-03-16 05:07:53.471739
842	2	login	user	2	\N	\N	\N	2026-03-16 05:11:21.885352
843	2	login	user	2	\N	\N	\N	2026-03-16 05:17:38.057316
844	2	login	user	2	\N	\N	\N	2026-03-16 05:24:43.650129
845	2	login	user	2	\N	\N	\N	2026-03-16 05:27:56.945209
846	2	login	user	2	\N	\N	\N	2026-03-16 05:30:52.674547
847	2	login	user	2	\N	\N	\N	2026-03-16 05:41:51.421687
848	2	login	user	2	\N	\N	\N	2026-03-16 05:44:09.224175
849	2	login	user	2	\N	\N	\N	2026-03-16 05:55:36.449069
850	2	login	user	2	\N	\N	\N	2026-03-16 06:06:45.139645
851	2	login	user	2	\N	\N	\N	2026-03-16 06:12:43.967097
852	2	login	user	2	\N	\N	\N	2026-03-16 06:21:15.192995
853	2	login	user	2	\N	\N	\N	2026-03-16 06:24:36.625294
854	2	login	user	2	\N	\N	\N	2026-03-16 06:28:24.739614
855	2	login	user	2	\N	\N	\N	2026-03-16 06:34:30.880314
856	2	login	user	2	\N	\N	\N	2026-03-16 06:41:46.495159
857	2	login	user	2	\N	\N	\N	2026-03-16 06:42:16.607176
858	2	login	user	2	\N	\N	\N	2026-03-16 06:59:11.458076
859	2	login	user	2	\N	\N	\N	2026-03-16 07:13:19.895578
860	2	login	user	2	\N	\N	\N	2026-03-16 08:45:25.340253
861	2	login	user	2	\N	\N	\N	2026-03-16 08:47:05.201878
862	2	login	user	2	\N	\N	\N	2026-03-16 08:47:30.058045
863	2	login	user	2	\N	\N	\N	2026-03-16 08:50:37.02959
864	2	login	user	2	\N	\N	\N	2026-03-16 10:12:28.284657
865	2	login	user	2	\N	\N	\N	2026-03-16 10:50:41.632401
866	2	login	user	2	\N	\N	\N	2026-03-16 11:02:08.538743
867	2	login	user	2	\N	\N	\N	2026-03-16 11:02:28.759444
868	2	login	user	2	\N	\N	\N	2026-03-16 11:09:09.492851
869	2	login	user	2	\N	\N	\N	2026-03-16 11:11:18.058795
870	2	login	user	2	\N	\N	\N	2026-03-16 12:58:54.929083
871	2	login	user	2	\N	\N	\N	2026-03-16 13:04:02.254698
872	2	login	user	2	\N	\N	\N	2026-03-16 13:10:03.727853
873	2	login	user	2	\N	\N	\N	2026-03-16 13:15:15.306507
874	2	login	user	2	\N	\N	\N	2026-03-16 13:43:20.880391
875	2	login	user	2	\N	\N	\N	2026-03-16 13:58:20.262968
876	2	login	user	2	\N	\N	\N	2026-03-16 13:59:56.038003
877	2	login	user	2	\N	\N	\N	2026-03-16 14:04:21.279667
878	2	login	user	2	\N	\N	\N	2026-03-16 14:16:46.650752
879	2	login	user	2	\N	\N	\N	2026-03-16 14:23:28.427915
880	2	login	user	2	\N	\N	\N	2026-03-16 14:28:48.834257
881	2	login	user	2	\N	\N	\N	2026-03-16 14:36:44.320214
882	2	login	user	2	\N	\N	\N	2026-03-16 15:05:01.881152
883	2	login	user	2	\N	\N	\N	2026-03-17 00:19:27.171579
884	2	login	user	2	\N	\N	\N	2026-03-17 00:27:13.229248
885	2	login	user	2	\N	\N	\N	2026-03-17 00:38:42.044185
886	2	login	user	2	\N	\N	\N	2026-03-17 00:46:41.339817
887	2	login	user	2	\N	\N	\N	2026-03-17 00:54:12.091611
888	2	login	user	2	\N	\N	\N	2026-03-17 01:13:55.034793
889	2	login	user	2	\N	\N	\N	2026-03-17 01:21:51.255927
890	2	login	user	2	\N	\N	\N	2026-03-17 01:25:44.981863
891	2	login	user	2	\N	\N	\N	2026-03-17 01:35:48.33719
892	2	login	user	2	\N	\N	\N	2026-03-17 01:41:15.24048
893	2	login	user	2	\N	\N	\N	2026-03-17 02:24:42.547743
894	2	login	user	2	\N	\N	\N	2026-03-17 02:31:07.395703
895	2	login	user	2	\N	\N	\N	2026-03-17 02:37:42.395501
896	2	login	user	2	\N	\N	\N	2026-03-17 02:43:12.345875
897	2	login	user	2	\N	\N	\N	2026-03-17 02:45:22.998911
898	2	login	user	2	\N	\N	\N	2026-03-17 02:49:10.759629
899	2	login	user	2	\N	\N	\N	2026-03-17 02:52:44.383964
900	2	login	user	2	\N	\N	\N	2026-03-17 03:00:07.041171
901	2	login	user	2	\N	\N	\N	2026-03-17 04:00:39.978849
902	2	login	user	2	\N	\N	\N	2026-03-17 04:05:05.379252
903	2	login	user	2	\N	\N	\N	2026-03-17 04:13:02.557349
904	2	login	user	2	\N	\N	\N	2026-03-17 04:21:48.299119
905	2	login	user	2	\N	\N	\N	2026-03-17 04:22:53.364885
906	2	login	user	2	\N	\N	\N	2026-03-17 04:34:38.161904
907	2	login	user	2	\N	\N	\N	2026-03-17 04:37:20.571922
908	2	login	user	2	\N	\N	\N	2026-03-17 05:35:04.452857
909	2	login	user	2	\N	\N	\N	2026-03-17 05:36:54.819704
910	2	login	user	2	\N	\N	\N	2026-03-17 05:45:03.15334
911	2	login	user	2	\N	\N	\N	2026-03-17 06:00:48.46721
912	2	login	user	2	\N	\N	\N	2026-03-17 06:05:23.295994
913	2	login	user	2	\N	\N	\N	2026-03-17 06:10:09.595822
914	2	login	user	2	\N	\N	\N	2026-03-17 06:18:22.62926
915	2	login	user	2	\N	\N	\N	2026-03-17 06:24:45.578496
916	2	login	user	2	\N	\N	\N	2026-03-17 06:27:14.231121
917	2	login	user	2	\N	\N	\N	2026-03-17 06:36:33.969714
918	2	login	user	2	\N	\N	\N	2026-03-17 06:45:40.913116
919	2	login	user	2	\N	\N	\N	2026-03-17 06:49:29.252022
920	2	login	user	2	\N	\N	\N	2026-03-17 06:53:44.884764
921	2	login	user	2	\N	\N	\N	2026-03-17 07:05:06.365276
922	2	login	user	2	\N	\N	\N	2026-03-17 07:17:11.428814
923	2	login	user	2	\N	\N	\N	2026-03-17 07:32:53.476623
924	2	login	user	2	\N	\N	\N	2026-03-17 07:46:42.454956
925	2	login	user	2	\N	\N	\N	2026-03-17 07:58:39.554262
926	2	login	user	2	\N	\N	\N	2026-03-17 08:06:00.373889
927	2	login	user	2	\N	\N	\N	2026-03-17 08:17:59.537833
928	2	login	user	2	\N	\N	\N	2026-03-17 08:21:37.120634
929	2	login	user	2	\N	\N	\N	2026-03-17 08:26:02.399433
930	2	login	user	2	\N	\N	\N	2026-03-17 08:37:41.836211
931	2	login	user	2	\N	\N	\N	2026-03-17 08:49:34.82573
932	2	login	user	2	\N	\N	\N	2026-03-17 13:18:44.293022
933	2	login	user	2	\N	\N	\N	2026-03-17 13:20:16.622748
934	2	login	user	2	\N	\N	\N	2026-03-17 13:24:50.595511
935	2	login	user	2	\N	\N	\N	2026-03-17 13:30:38.865995
936	2	login	user	2	\N	\N	\N	2026-03-17 13:43:17.982474
937	2	login	user	2	\N	\N	\N	2026-03-18 00:12:23.201009
938	2	login	user	2	\N	\N	\N	2026-03-18 00:24:34.732439
939	2	login	user	2	\N	\N	\N	2026-03-18 00:33:46.56811
940	2	login	user	2	\N	\N	\N	2026-03-18 00:41:34.902955
941	2	login	user	2	\N	\N	\N	2026-03-18 00:50:11.628228
942	2	login	user	2	\N	\N	\N	2026-03-18 00:55:52.344196
943	2	login	user	2	\N	\N	\N	2026-03-18 01:04:00.037659
944	2	login	user	2	\N	\N	\N	2026-03-18 01:17:03.225662
945	2	login	user	2	\N	\N	\N	2026-03-18 01:17:49.30173
946	2	login	user	2	\N	\N	\N	2026-03-18 01:33:19.143358
947	2	login	user	2	\N	\N	\N	2026-03-18 01:40:13.316402
948	2	login	user	2	\N	\N	\N	2026-03-18 01:45:43.10892
949	2	login	user	2	\N	\N	\N	2026-03-18 01:46:11.514944
950	2	login	user	2	\N	\N	\N	2026-03-18 01:54:37.346304
951	2	login	user	2	\N	\N	\N	2026-03-18 01:59:30.928532
952	2	login	user	2	\N	\N	\N	2026-03-18 02:02:13.956394
953	2	login	user	2	\N	\N	\N	2026-03-18 02:05:28.001374
954	2	login	user	2	\N	\N	\N	2026-03-18 02:06:43.24296
955	2	login	user	2	\N	\N	\N	2026-03-18 02:17:25.94561
956	2	login	user	2	\N	\N	\N	2026-03-18 02:17:59.494226
957	2	login	user	2	\N	\N	\N	2026-03-18 02:24:02.373226
958	2	login	user	2	\N	\N	\N	2026-03-18 02:39:59.126869
959	2	login	user	2	\N	\N	\N	2026-03-18 02:44:04.105417
960	2	login	user	2	\N	\N	\N	2026-03-18 02:49:17.432744
961	2	login	user	2	\N	\N	\N	2026-03-18 02:55:00.38543
962	2	login	user	2	\N	\N	\N	2026-03-18 06:12:27.360064
963	2	login	user	2	\N	\N	\N	2026-03-18 06:21:45.39891
964	2	login	user	2	\N	\N	\N	2026-03-18 06:44:33.266883
965	2	login	user	2	\N	\N	\N	2026-03-18 07:12:55.185162
966	2	login	user	2	\N	\N	\N	2026-03-18 07:29:08.899612
967	2	login	user	2	\N	\N	\N	2026-03-18 07:29:23.099794
968	2	login	user	2	\N	\N	\N	2026-03-18 07:43:10.399794
969	2	login	user	2	\N	\N	\N	2026-03-18 07:48:29.960822
970	2	login	user	2	\N	\N	\N	2026-03-18 08:02:22.29463
971	2	login	user	2	\N	\N	\N	2026-03-18 08:09:05.033129
972	2	login	user	2	\N	\N	\N	2026-03-18 08:12:45.88981
973	2	login	user	2	\N	\N	\N	2026-03-18 08:28:49.145219
974	2	login	user	2	\N	\N	\N	2026-03-18 08:53:57.75414
975	2	login	user	2	\N	\N	\N	2026-03-18 13:06:06.494521
976	2	login	user	2	\N	\N	\N	2026-03-18 13:09:23.171522
977	2	login	user	2	\N	\N	\N	2026-03-18 13:12:18.16076
978	2	login	user	2	\N	\N	\N	2026-03-18 13:20:26.780957
979	2	login	user	2	\N	\N	\N	2026-03-18 13:23:04.150319
980	2	login	user	2	\N	\N	\N	2026-03-18 13:26:05.95076
981	2	login	user	2	\N	\N	\N	2026-03-18 13:27:20.996126
982	2	login	user	2	\N	\N	\N	2026-03-18 13:29:56.899653
983	2	login	user	2	\N	\N	\N	2026-03-18 13:34:10.705409
984	2	login	user	2	\N	\N	\N	2026-03-18 14:01:23.534648
985	2	login	user	2	\N	\N	\N	2026-03-18 14:04:14.136195
986	2	login	user	2	\N	\N	\N	2026-03-19 00:49:19.439712
987	2	login	user	2	\N	\N	\N	2026-03-19 01:19:24.879865
988	2	login	user	2	\N	\N	\N	2026-03-19 01:27:45.098794
989	2	login	user	2	\N	\N	\N	2026-03-19 01:46:28.184006
990	2	login	user	2	\N	\N	\N	2026-03-19 04:10:47.546045
991	2	login	user	2	\N	\N	\N	2026-03-19 04:19:44.906119
992	2	login	user	2	\N	\N	\N	2026-03-19 05:04:54.960112
993	2	login	user	2	\N	\N	\N	2026-03-19 05:25:00.908356
994	2	login	user	2	\N	\N	\N	2026-03-19 05:27:55.717059
995	2	login	user	2	\N	\N	\N	2026-03-19 06:47:41.755766
996	2	login	user	2	\N	\N	\N	2026-03-19 06:55:33.15573
997	2	login	user	2	\N	\N	\N	2026-03-19 07:01:50.235034
998	2	login	user	2	\N	\N	\N	2026-03-19 07:16:39.26874
999	2	login	user	2	\N	\N	\N	2026-03-19 07:21:38.961795
1000	2	login	user	2	\N	\N	\N	2026-03-19 07:24:14.514923
1001	2	login	user	2	\N	\N	\N	2026-03-19 07:29:33.530183
1002	2	login	user	2	\N	\N	\N	2026-03-19 07:33:00.545387
1003	2	login	user	2	\N	\N	\N	2026-03-19 07:36:01.205863
1004	2	login	user	2	\N	\N	\N	2026-03-19 07:46:27.288287
1005	2	login	user	2	\N	\N	\N	2026-03-19 07:59:50.322349
1006	2	login	user	2	\N	\N	\N	2026-03-19 08:07:34.539518
1007	2	login	user	2	\N	\N	\N	2026-03-19 08:11:03.709737
1008	2	login	user	2	\N	\N	\N	2026-03-19 08:13:14.086861
1009	2	login	user	2	\N	\N	\N	2026-03-19 08:15:48.889899
1010	2	login	user	2	\N	\N	\N	2026-03-19 08:22:57.284574
1011	2	login	user	2	\N	\N	\N	2026-03-19 08:30:52.950924
1012	2	login	user	2	\N	\N	\N	2026-03-19 08:40:48.283887
1013	2	login	user	2	\N	\N	\N	2026-03-19 08:43:32.423748
1014	2	login	user	2	\N	\N	\N	2026-03-20 00:09:33.697814
1015	2	login	user	2	\N	\N	\N	2026-03-20 01:25:48.487331
1016	2	login	user	2	\N	\N	\N	2026-03-20 01:32:22.047069
1017	2	login	user	2	\N	\N	\N	2026-03-20 01:50:54.783725
1018	2	login	user	2	\N	\N	\N	2026-03-20 02:14:54.01726
1019	2	login	user	2	\N	\N	\N	2026-03-20 02:23:28.231152
1020	2	login	user	2	\N	\N	\N	2026-03-20 02:50:03.865985
1021	2	login	user	2	\N	\N	\N	2026-03-20 03:05:50.964431
1022	2	login	user	2	\N	\N	\N	2026-03-20 03:14:10.825169
1023	2	login	user	2	\N	\N	\N	2026-03-20 03:22:01.830987
1024	2	login	user	2	\N	\N	\N	2026-03-20 03:53:33.896821
1025	2	login	user	2	\N	\N	\N	2026-03-20 03:56:13.133708
1026	2	login	user	2	\N	\N	\N	2026-03-20 04:07:06.714256
1027	2	login	user	2	\N	\N	\N	2026-03-20 04:13:57.020402
1028	2	login	user	2	\N	\N	\N	2026-03-20 04:16:05.500588
1029	2	login	user	2	\N	\N	\N	2026-03-20 04:18:14.401421
1030	2	login	user	2	\N	\N	\N	2026-03-20 04:26:38.615791
1031	2	login	user	2	\N	\N	\N	2026-03-20 04:30:12.516859
1032	2	login	user	2	\N	\N	\N	2026-03-20 04:34:50.696472
1033	2	login	user	2	\N	\N	\N	2026-03-20 04:44:56.533863
1034	2	login	user	2	\N	\N	\N	2026-03-20 04:47:00.225314
1035	2	login	user	2	\N	\N	\N	2026-03-20 04:47:59.688624
1036	2	login	user	2	\N	\N	\N	2026-03-20 04:54:11.032374
1037	2	login	user	2	\N	\N	\N	2026-03-20 04:56:53.544485
1038	2	login	user	2	\N	\N	\N	2026-03-20 04:59:55.627586
1039	2	login	user	2	\N	\N	\N	2026-03-20 05:02:38.444237
1040	2	login	user	2	\N	\N	\N	2026-03-20 05:09:15.183405
1041	2	login	user	2	\N	\N	\N	2026-03-20 05:14:17.659589
1042	2	login	user	2	\N	\N	\N	2026-03-20 05:22:18.75716
1043	2	login	user	2	\N	\N	\N	2026-03-20 05:26:56.159731
1044	2	login	user	2	\N	\N	\N	2026-03-20 05:29:34.003903
1045	2	login	user	2	\N	\N	\N	2026-03-20 05:35:39.63746
1046	2	login	user	2	\N	\N	\N	2026-03-20 05:42:51.433973
1047	2	login	user	2	\N	\N	\N	2026-03-20 05:43:23.546441
1048	2	login	user	2	\N	\N	\N	2026-03-20 05:47:45.249074
1049	2	login	user	2	\N	\N	\N	2026-03-20 10:20:33.560892
1050	2	login	user	2	\N	\N	\N	2026-03-20 10:27:36.420925
1051	2	login	user	2	\N	\N	\N	2026-03-20 10:52:12.209656
1052	2	login	user	2	\N	\N	\N	2026-03-20 10:55:11.151967
1053	2	login	user	2	\N	\N	\N	2026-03-20 11:02:39.683332
1054	2	login	user	2	\N	\N	\N	2026-03-20 15:16:09.656588
1055	2	login	user	2	\N	\N	\N	2026-03-22 04:35:28.828483
1056	2	login	user	2	\N	\N	\N	2026-03-22 04:42:06.432338
1057	2	login	user	2	\N	\N	\N	2026-03-22 04:47:00.10918
1058	2	login	user	2	\N	\N	\N	2026-03-22 04:55:18.590366
1059	2	login	user	2	\N	\N	\N	2026-03-22 05:14:55.672708
1060	2	login	user	2	\N	\N	\N	2026-03-22 05:58:39.175187
1061	2	login	user	2	\N	\N	\N	2026-03-22 06:12:45.748044
1062	2	login	user	2	\N	\N	\N	2026-03-22 06:21:19.84773
1063	2	login	user	2	\N	\N	\N	2026-03-22 06:32:37.71671
1064	2	login	user	2	\N	\N	\N	2026-03-22 12:35:24.873638
1065	2	login	user	2	\N	\N	\N	2026-03-22 12:37:57.275385
1066	2	login	user	2	\N	\N	\N	2026-03-22 12:47:29.937505
1067	2	login	user	2	\N	\N	\N	2026-03-23 00:55:36.493249
1068	2	login	user	2	\N	\N	\N	2026-03-23 01:08:48.939137
1069	2	login	user	2	\N	\N	\N	2026-03-23 01:31:00.658197
1070	2	login	user	2	\N	\N	\N	2026-03-23 05:23:39.442298
1071	2	login	user	2	\N	\N	\N	2026-03-23 05:46:33.075936
1072	2	login	user	2	\N	\N	\N	2026-03-23 05:58:34.513378
1073	2	login	user	2	\N	\N	\N	2026-03-23 08:40:58.875125
1074	2	login	user	2	\N	\N	\N	2026-03-23 13:41:27.855904
1075	2	login	user	2	\N	\N	\N	2026-03-23 13:46:37.659665
1076	2	login	user	2	\N	\N	\N	2026-03-23 13:51:35.176911
1077	2	login	user	2	\N	\N	\N	2026-03-23 13:55:56.791314
1078	2	login	user	2	\N	\N	\N	2026-03-24 01:27:34.238115
1079	2	login	user	2	\N	\N	\N	2026-03-24 01:30:55.618222
1080	2	login	user	2	\N	\N	\N	2026-03-24 01:34:48.544622
1081	2	login	user	2	\N	\N	\N	2026-03-24 01:39:25.247521
1082	2	login	user	2	\N	\N	\N	2026-03-24 01:45:09.166813
1083	2	login	user	2	\N	\N	\N	2026-03-24 01:55:45.698101
1084	2	login	user	2	\N	\N	\N	2026-03-24 02:01:05.166542
1085	2	login	user	2	\N	\N	\N	2026-03-24 02:12:27.255223
1086	2	login	user	2	\N	\N	\N	2026-03-24 03:50:37.91555
1087	2	login	user	2	\N	\N	\N	2026-03-24 04:30:34.026818
1088	2	login	user	2	\N	\N	\N	2026-03-24 04:32:32.485367
1089	2	login	user	2	\N	\N	\N	2026-03-24 04:46:12.101037
1090	2	login	user	2	\N	\N	\N	2026-03-24 04:56:36.36317
1091	2	login	user	2	\N	\N	\N	2026-03-24 05:03:38.028784
1092	2	login	user	2	\N	\N	\N	2026-03-24 05:07:40.033115
1093	2	login	user	2	\N	\N	\N	2026-03-24 05:14:22.122692
1094	2	login	user	2	\N	\N	\N	2026-03-24 05:18:58.194495
1095	2	login	user	2	\N	\N	\N	2026-03-24 05:25:03.363869
1096	2	login	user	2	\N	\N	\N	2026-03-24 05:28:14.604604
1097	2	login	user	2	\N	\N	\N	2026-03-24 05:38:13.983382
1098	2	login	user	2	\N	\N	\N	2026-03-25 00:21:16.835742
1099	2	login	user	2	\N	\N	\N	2026-03-25 00:39:43.346143
1100	2	login	user	2	\N	\N	\N	2026-03-25 00:43:31.08275
1101	2	login	user	2	\N	\N	\N	2026-03-25 00:47:41.568439
1102	2	login	user	2	\N	\N	\N	2026-03-25 00:56:51.834378
1103	2	login	user	2	\N	\N	\N	2026-03-25 00:59:32.133443
1104	2	login	user	2	\N	\N	\N	2026-03-25 01:11:25.991032
1105	2	login	user	2	\N	\N	\N	2026-03-25 01:20:29.150797
1106	2	login	user	2	\N	\N	\N	2026-03-25 01:21:44.997263
1107	2	login	user	2	\N	\N	\N	2026-03-25 01:31:39.861891
1108	2	login	user	2	\N	\N	\N	2026-03-25 01:36:06.87916
1109	2	login	user	2	\N	\N	\N	2026-03-25 01:38:08.130722
1110	2	login	user	2	\N	\N	\N	2026-03-25 01:40:41.270259
1111	2	login	user	2	\N	\N	\N	2026-03-25 01:41:56.559436
1112	2	login	user	2	\N	\N	\N	2026-03-25 04:28:51.217057
1113	2	login	user	2	\N	\N	\N	2026-03-25 04:50:01.790822
1114	2	login	user	2	\N	\N	\N	2026-03-25 04:55:43.025399
1115	2	login	user	2	\N	\N	\N	2026-03-25 05:16:01.843073
1116	2	login	user	2	\N	\N	\N	2026-03-25 05:20:00.592772
1117	2	login	user	2	\N	\N	\N	2026-03-25 05:31:10.726569
1118	2	login	user	2	\N	\N	\N	2026-03-25 05:40:06.368277
1119	2	login	user	2	\N	\N	\N	2026-03-25 05:51:04.092935
1120	2	login	user	2	\N	\N	\N	2026-03-25 06:03:15.331434
1121	2	login	user	2	\N	\N	\N	2026-03-25 06:09:08.166129
1122	2	login	user	2	\N	\N	\N	2026-03-25 06:20:03.08743
1123	2	login	user	2	\N	\N	\N	2026-03-25 06:21:01.146227
1124	2	login	user	2	\N	\N	\N	2026-03-25 06:41:02.780772
1125	2	login	user	2	\N	\N	\N	2026-03-25 06:45:12.449571
1126	2	login	user	2	\N	\N	\N	2026-03-25 07:33:44.870793
1127	2	login	user	2	\N	\N	\N	2026-03-25 07:46:25.677485
1128	2	login	user	2	\N	\N	\N	2026-03-25 07:55:30.050968
1129	2	login	user	2	\N	\N	\N	2026-03-25 08:09:22.207412
1130	2	login	user	2	\N	\N	\N	2026-03-25 08:13:58.82622
1131	2	login	user	2	\N	\N	\N	2026-03-25 08:18:34.725652
1132	2	login	user	2	\N	\N	\N	2026-03-25 08:21:17.066064
1133	2	login	user	2	\N	\N	\N	2026-03-25 08:37:16.293442
1134	2	login	user	2	\N	\N	\N	2026-03-25 08:39:47.581412
1135	2	login	user	2	\N	\N	\N	2026-03-25 08:46:50.745686
1136	2	login	user	2	\N	\N	\N	2026-03-26 00:43:39.350079
1137	2	login	user	2	\N	\N	\N	2026-03-26 00:46:37.617526
1138	2	login	user	2	\N	\N	\N	2026-03-26 00:51:28.098015
1139	2	login	user	2	\N	\N	\N	2026-03-26 00:55:33.259606
1140	2	login	user	2	\N	\N	\N	2026-03-26 01:22:20.967278
1141	2	login	user	2	\N	\N	\N	2026-03-26 01:28:16.025427
1142	2	login	user	2	\N	\N	\N	2026-03-26 01:36:45.273997
1143	2	login	user	2	\N	\N	\N	2026-03-26 01:46:24.900144
1144	2	login	user	2	\N	\N	\N	2026-03-26 01:59:25.153143
1145	2	login	user	2	\N	\N	\N	2026-03-26 02:02:45.78342
1146	2	login	user	2	\N	\N	\N	2026-03-26 02:12:47.342609
1147	2	login	user	2	\N	\N	\N	2026-03-26 02:17:11.729241
1148	2	login	user	2	\N	\N	\N	2026-03-26 02:23:31.158563
1149	2	login	user	2	\N	\N	\N	2026-03-26 02:29:30.734431
1150	2	login	user	2	\N	\N	\N	2026-03-26 02:40:27.298908
1151	2	login	user	2	\N	\N	\N	2026-03-27 01:05:37.511157
1152	2	login	user	2	\N	\N	\N	2026-03-27 01:24:09.324368
1153	2	login	user	2	\N	\N	\N	2026-03-27 01:33:57.907274
1154	2	login	user	2	\N	\N	\N	2026-03-27 01:45:28.062235
1155	2	login	user	2	\N	\N	\N	2026-03-27 05:00:38.672652
1156	2	login	user	2	\N	\N	\N	2026-03-27 05:41:06.628929
1157	2	login	user	2	\N	\N	\N	2026-03-27 05:45:40.790858
1158	2	login	user	2	\N	\N	\N	2026-03-27 05:53:43.311373
1159	2	login	user	2	\N	\N	\N	2026-03-27 06:23:04.396876
1160	2	login	user	2	\N	\N	\N	2026-03-27 06:27:17.319238
1161	2	login	user	2	\N	\N	\N	2026-03-27 06:30:43.958741
1162	2	login	user	2	\N	\N	\N	2026-03-27 06:48:53.69412
1163	2	login	user	2	\N	\N	\N	2026-03-27 06:53:32.965735
1164	2	login	user	2	\N	\N	\N	2026-03-27 07:45:24.843719
1165	2	login	user	2	\N	\N	\N	2026-03-27 07:56:36.195939
1166	2	login	user	2	\N	\N	\N	2026-03-27 08:27:26.823269
1167	2	login	user	2	\N	\N	\N	2026-03-27 14:45:54.81427
1168	2	login	user	2	\N	\N	\N	2026-03-28 02:21:46.260499
1169	2	login	user	2	\N	\N	\N	2026-03-28 02:30:29.850406
1170	2	login	user	2	\N	\N	\N	2026-03-28 02:34:12.116828
1171	2	login	user	2	\N	\N	\N	2026-03-28 02:38:19.322045
1172	2	login	user	2	\N	\N	\N	2026-03-28 02:39:54.166933
1173	2	login	user	2	\N	\N	\N	2026-03-28 02:45:25.018919
1174	2	login	user	2	\N	\N	\N	2026-03-28 02:50:48.094311
1175	2	login	user	2	\N	\N	\N	2026-03-28 03:07:59.672858
1176	2	login	user	2	\N	\N	\N	2026-03-28 03:24:28.64654
1177	2	login	user	2	\N	\N	\N	2026-03-28 03:35:27.228043
1178	2	login	user	2	\N	\N	\N	2026-03-28 13:26:08.64378
1179	2	login	user	2	\N	\N	\N	2026-03-28 14:00:17.50091
1180	2	login	user	2	\N	\N	\N	2026-03-29 05:30:59.469336
1181	2	login	user	2	\N	\N	\N	2026-03-29 05:38:34.745983
1182	2	login	user	2	\N	\N	\N	2026-03-29 06:31:49.022993
1183	2	login	user	2	\N	\N	\N	2026-03-29 06:52:14.723329
1184	2	login	user	2	\N	\N	\N	2026-03-29 08:33:10.859489
1185	2	login	user	2	\N	\N	\N	2026-03-29 08:58:13.181547
1186	2	login	user	2	\N	\N	\N	2026-03-29 09:09:52.88523
1187	2	login	user	2	\N	\N	\N	2026-03-29 09:37:04.352474
1188	2	login	user	2	\N	\N	\N	2026-03-29 09:58:37.022906
1189	2	login	user	2	\N	\N	\N	2026-03-29 10:07:32.95354
1190	2	login	user	2	\N	\N	\N	2026-03-29 10:11:41.874865
1191	2	login	user	2	\N	\N	\N	2026-03-29 11:06:18.814769
1192	2	login	user	2	\N	\N	\N	2026-03-29 11:11:10.329843
1193	2	login	user	2	\N	\N	\N	2026-03-29 11:25:21.673959
1194	2	login	user	2	\N	\N	\N	2026-03-29 11:37:35.020892
1195	2	login	user	2	\N	\N	\N	2026-03-29 13:29:53.176015
1196	2	login	user	2	\N	\N	\N	2026-03-29 13:45:54.361075
1197	2	login	user	2	\N	\N	\N	2026-03-29 13:56:49.322291
1198	2	login	user	2	\N	\N	\N	2026-03-29 14:06:26.649549
1199	2	login	user	2	\N	\N	\N	2026-03-30 00:22:02.788606
1200	2	login	user	2	\N	\N	\N	2026-03-30 00:39:16.4423
1201	2	login	user	2	\N	\N	\N	2026-03-30 00:40:56.487108
1202	2	login	user	2	\N	\N	\N	2026-03-30 01:19:24.342978
1203	2	login	user	2	\N	\N	\N	2026-03-30 01:47:03.223901
1204	2	login	user	2	\N	\N	\N	2026-03-30 02:07:36.187397
1205	2	login	user	2	\N	\N	\N	2026-03-30 02:36:36.505104
1206	2	login	user	2	\N	\N	\N	2026-03-30 03:06:18.624466
1207	2	login	user	2	\N	\N	\N	2026-03-30 05:22:46.922429
1208	2	login	user	2	\N	\N	\N	2026-03-30 05:36:18.753594
1209	2	login	user	2	\N	\N	\N	2026-03-30 05:38:38.608045
1210	2	login	user	2	\N	\N	\N	2026-03-30 05:49:22.672313
1211	2	login	user	2	\N	\N	\N	2026-03-30 07:21:57.196183
1213	2	login	user	2	\N	\N	\N	2026-03-30 07:34:21.131944
1215	2	login	user	2	\N	\N	\N	2026-03-30 08:09:50.98595
1217	2	login	user	2	\N	\N	\N	2026-03-30 08:44:51.479594
1219	2	login	user	2	\N	\N	\N	2026-03-31 00:16:23.989328
1221	2	login	user	2	\N	\N	\N	2026-03-31 00:54:00.221963
1223	2	login	user	2	\N	\N	\N	2026-03-31 01:59:04.905427
1225	2	login	user	2	\N	\N	\N	2026-03-31 02:23:21.494221
1227	2	login	user	2	\N	\N	\N	2026-03-31 04:56:30.858744
1229	2	login	user	2	\N	\N	\N	2026-03-31 05:22:03.257622
1231	2	login	user	2	\N	\N	\N	2026-03-31 07:38:22.053958
1232	2	login	user	2	\N	\N	\N	2026-03-31 07:43:12.289437
1233	2	login	user	2	\N	\N	\N	2026-03-31 08:06:50.985795
1234	2	login	user	2	\N	\N	\N	2026-03-31 08:09:44.186004
1235	2	login	user	2	\N	\N	\N	2026-03-31 08:14:17.723352
1236	2	login	user	2	\N	\N	\N	2026-03-31 08:20:37.927594
1237	2	login	user	2	\N	\N	\N	2026-03-31 08:22:33.887719
1238	2	login	user	2	\N	\N	\N	2026-03-31 08:29:09.169491
1239	2	login	user	2	\N	\N	\N	2026-03-31 08:31:23.452513
1240	2	login	user	2	\N	\N	\N	2026-03-31 08:35:04.869516
1241	2	login	user	2	\N	\N	\N	2026-03-31 08:40:25.845933
1242	2	login	user	2	\N	\N	\N	2026-03-31 08:42:10.862498
1243	2	login	user	2	\N	\N	\N	2026-03-31 08:42:46.889826
1244	2	login	user	2	\N	\N	\N	2026-03-31 08:45:41.286917
1245	2	login	user	2	\N	\N	\N	2026-03-31 08:45:58.37315
1246	2	login	user	2	\N	\N	\N	2026-03-31 14:18:41.04536
1247	2	login	user	2	\N	\N	\N	2026-03-31 14:27:27.72243
1248	2	login	user	2	\N	\N	\N	2026-03-31 14:33:00.411601
1249	2	login	user	2	\N	\N	\N	2026-03-31 15:00:43.318901
1250	2	login	user	2	\N	\N	\N	2026-03-31 15:10:35.191996
1251	2	login	user	2	\N	\N	\N	2026-03-31 15:17:11.946167
1252	2	login	user	2	\N	\N	\N	2026-04-01 00:22:24.511258
1253	2	login	user	2	\N	\N	\N	2026-04-01 00:39:51.948146
1254	2	login	user	2	\N	\N	\N	2026-04-01 00:42:41.930174
1255	2	login	user	2	\N	\N	\N	2026-04-01 00:45:59.103627
1256	2	login	user	2	\N	\N	\N	2026-04-01 00:48:07.70789
1257	2	login	user	2	\N	\N	\N	2026-04-01 00:49:53.58811
1258	2	login	user	2	\N	\N	\N	2026-04-01 00:51:26.624947
1259	2	login	user	2	\N	\N	\N	2026-04-01 01:11:29.69591
1260	2	login	user	2	\N	\N	\N	2026-04-01 01:24:24.509881
1261	2	login	user	2	\N	\N	\N	2026-04-01 01:49:26.349093
1262	2	login	user	2	\N	\N	\N	2026-04-01 02:23:40.04234
1263	2	login	user	2	\N	\N	\N	2026-04-01 02:30:18.136399
1264	2	login	user	2	\N	\N	\N	2026-04-01 02:31:25.336631
1265	2	login	user	2	\N	\N	\N	2026-04-01 02:34:02.366231
1266	2	login	user	2	\N	\N	\N	2026-04-01 02:41:23.540135
1267	2	login	user	2	\N	\N	\N	2026-04-01 02:43:25.113083
1268	2	login	user	2	\N	\N	\N	2026-04-01 02:43:55.533452
1269	2	login	user	2	\N	\N	\N	2026-04-01 02:59:45.509903
1270	2	login	user	2	\N	\N	\N	2026-04-01 03:00:50.558631
1271	2	login	user	2	\N	\N	\N	2026-04-01 03:04:14.645042
1272	2	login	user	2	\N	\N	\N	2026-04-01 03:04:28.886834
1273	2	login	user	2	\N	\N	\N	2026-04-01 03:05:38.5032
1274	2	login	user	2	\N	\N	\N	2026-04-01 03:06:17.138208
1275	2	login	user	2	\N	\N	\N	2026-04-01 03:57:35.501447
1276	2	login	user	2	\N	\N	\N	2026-04-01 03:57:52.011833
1277	2	login	user	2	\N	\N	\N	2026-04-01 04:00:51.115804
1278	2	login	user	2	\N	\N	\N	2026-04-01 04:09:44.581584
1279	2	login	user	2	\N	\N	\N	2026-04-01 04:37:42.356772
1280	2	login	user	2	\N	\N	\N	2026-04-01 04:47:54.053688
1281	2	login	user	2	\N	\N	\N	2026-04-01 04:50:16.033679
1282	2	login	user	2	\N	\N	\N	2026-04-01 05:05:19.275627
1283	2	login	user	2	\N	\N	\N	2026-04-01 05:08:39.558268
1284	2	login	user	2	\N	\N	\N	2026-04-01 05:11:14.324236
1285	2	login	user	2	\N	\N	\N	2026-04-01 05:20:46.17758
1286	2	login	user	2	\N	\N	\N	2026-04-01 06:09:47.882183
1287	2	login	user	2	\N	\N	\N	2026-04-01 07:12:39.550751
1288	2	login	user	2	\N	\N	\N	2026-04-01 07:14:06.717454
1289	2	login	user	2	\N	\N	\N	2026-04-01 07:15:19.029952
1290	2	login	user	2	\N	\N	\N	2026-04-01 07:18:52.521277
1291	2	login	user	2	\N	\N	\N	2026-04-01 08:22:23.586862
1292	2	login	user	2	\N	\N	\N	2026-04-01 08:48:15.113255
1293	2	login	user	2	\N	\N	\N	2026-04-01 13:52:15.871455
1294	2	login	user	2	\N	\N	\N	2026-04-01 13:53:52.193055
1295	2	login	user	2	\N	\N	\N	2026-04-01 13:59:33.088295
1296	2	login	user	2	\N	\N	\N	2026-04-01 14:05:25.563895
1297	2	login	user	2	\N	\N	\N	2026-04-01 14:35:02.522809
1298	2	login	user	2	\N	\N	\N	2026-04-01 14:51:21.65054
1299	2	login	user	2	\N	\N	\N	2026-04-01 14:52:28.738979
1300	2	login	user	2	\N	\N	\N	2026-04-01 14:55:07.027137
1301	2	login	user	2	\N	\N	\N	2026-04-01 14:58:21.406876
1302	2	login	user	2	\N	\N	\N	2026-04-01 15:00:49.056692
1303	2	login	user	2	\N	\N	\N	2026-04-01 15:03:11.976418
1304	2	login	user	2	\N	\N	\N	2026-04-01 15:05:18.11556
1305	2	login	user	2	\N	\N	\N	2026-04-02 00:03:14.998992
1306	2	login	user	2	\N	\N	\N	2026-04-02 00:08:49.656618
1307	2	login	user	2	\N	\N	\N	2026-04-02 00:13:03.598686
1308	2	login	user	2	\N	\N	\N	2026-04-02 00:41:37.467173
1309	2	login	user	2	\N	\N	\N	2026-04-02 00:57:37.297309
1310	2	login	user	2	\N	\N	\N	2026-04-02 00:58:56.66958
1311	2	login	user	2	\N	\N	\N	2026-04-02 01:01:03.902345
1312	2	login	user	2	\N	\N	\N	2026-04-02 01:02:45.533424
1313	2	login	user	2	\N	\N	\N	2026-04-02 01:17:14.534004
1314	2	login	user	2	\N	\N	\N	2026-04-02 01:20:47.49941
1315	2	login	user	2	\N	\N	\N	2026-04-02 01:23:42.425465
1316	2	login	user	2	\N	\N	\N	2026-04-02 01:44:07.250691
1317	2	login	user	2	\N	\N	\N	2026-04-02 01:52:02.350112
1318	2	login	user	2	\N	\N	\N	2026-04-02 02:01:05.554091
1319	2	login	user	2	\N	\N	\N	2026-04-02 02:04:50.99186
1320	\N	toggle_user_active	user	8	{"is_active": true}	{"is_active": false}	\N	2026-04-02 02:05:06.50674
1321	2	login	user	2	\N	\N	\N	2026-04-02 02:18:01.22089
1322	\N	toggle_user_active	user	8	{"is_active": false}	{"is_active": true}	\N	2026-04-02 02:18:05.504397
1323	2	login	user	2	\N	\N	\N	2026-04-02 02:26:06.073756
1324	\N	toggle_user_active	user	8	{"is_active": true}	{"is_active": false}	\N	2026-04-02 02:26:10.91496
1325	\N	toggle_user_active	user	8	{"is_active": false}	{"is_active": true}	\N	2026-04-02 02:26:12.272471
1326	\N	toggle_user_active	user	8	{"is_active": true}	{"is_active": false}	\N	2026-04-02 02:26:13.305745
1327	2	login	user	2	\N	\N	\N	2026-04-02 02:39:08.411234
1328	\N	toggle_user_active	user	8	{"is_active": false}	{"is_active": true}	\N	2026-04-02 02:39:14.183884
1329	\N	update_workstations	user	7	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-02 02:39:26.996398
1330	2	login	user	2	\N	\N	\N	2026-04-02 02:56:28.600074
1331	\N	toggle_user_active	user	8	{"is_active": true}	{"is_active": false}	\N	2026-04-02 02:56:37.85588
1332	\N	toggle_user_active	user	8	{"is_active": false}	{"is_active": true}	\N	2026-04-02 02:56:38.765715
1333	2	login	user	2	\N	\N	\N	2026-04-02 03:25:37.579689
1334	\N	update_workstations	user	8	{"workstations": null}	{"workstations": null}	\N	2026-04-02 03:26:03.45407
1335	\N	update_user_screen_permissions	user	8	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\"]"}	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"workshop_inventory\\"]"}	\N	2026-04-02 03:26:03.461033
1336	2	logout	user	2	\N	\N	\N	2026-04-02 03:26:06.024248
1337	8	login	user	8	\N	\N	\N	2026-04-02 03:26:18.285712
1338	8	logout	user	8	\N	\N	\N	2026-04-02 03:26:27.789035
1339	2	login	user	2	\N	\N	\N	2026-04-02 03:26:33.328073
1340	\N	update_workstations	user	8	{"workstations": null}	{"workstations": null}	\N	2026-04-02 03:28:16.337899
1341	\N	update_user_screen_permissions	user	8	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"workshop_inventory\\"]"}	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"workshop_inventory\\"]"}	\N	2026-04-02 03:28:16.343348
1342	\N	update_workstations	user	7	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-02 03:28:30.470993
1343	\N	update_user_screen_permissions	user	7	{"screen_permissions": "[\\"dashboard\\"]"}	{"screen_permissions": "[\\"dashboard\\"]"}	\N	2026-04-02 03:28:30.475342
1344	2	login	user	2	\N	\N	\N	2026-04-02 04:11:43.319035
1345	2	login	user	2	\N	\N	\N	2026-04-02 05:18:30.824625
1346	2	login	user	2	\N	\N	\N	2026-04-02 05:41:37.411314
1347	2	login	user	2	\N	\N	\N	2026-04-02 05:47:43.239614
1348	2	login	user	2	\N	\N	\N	2026-04-02 06:56:37.011385
1349	2	login	user	2	\N	\N	\N	2026-04-02 07:06:42.087634
1350	2	login	user	2	\N	\N	\N	2026-04-02 07:16:11.383547
1351	2	login	user	2	\N	\N	\N	2026-04-02 07:20:54.861488
1352	2	login	user	2	\N	\N	\N	2026-04-02 07:25:13.989472
1353	2	login	user	2	\N	\N	\N	2026-04-02 07:28:31.777609
1354	2	login	user	2	\N	\N	\N	2026-04-02 07:51:26.698278
1355	2	login	user	2	\N	\N	\N	2026-04-02 07:58:05.148161
1356	2	login	user	2	\N	\N	\N	2026-04-02 08:18:41.959117
1357	2	login	user	2	\N	\N	\N	2026-04-02 08:24:58.739538
1358	2	login	user	2	\N	\N	\N	2026-04-02 08:43:23.100742
1359	2	login	user	2	\N	\N	\N	2026-04-02 13:25:56.673494
1360	2	login	user	2	\N	\N	\N	2026-04-02 13:40:40.791981
1361	2	login	user	2	\N	\N	\N	2026-04-02 14:13:58.317588
1362	2	login	user	2	\N	\N	\N	2026-04-02 14:39:42.419176
1363	\N	income_item	item	404	{"quantity": 14}	{"quantity": 16}	\N	2026-04-02 14:39:55.340641
1364	2	login	user	2	\N	\N	\N	2026-04-03 00:18:09.442206
1365	2	login	user	2	\N	\N	\N	2026-04-03 00:27:00.002256
1366	2	login	user	2	\N	\N	\N	2026-04-03 00:35:02.465354
1367	2	login	user	2	\N	\N	\N	2026-04-03 00:38:17.764065
1368	2	login	user	2	\N	\N	\N	2026-04-03 00:43:05.974174
1369	2	login	user	2	\N	\N	\N	2026-04-03 00:47:10.195454
1370	2	login	user	2	\N	\N	\N	2026-04-03 00:49:38.871107
1371	2	login	user	2	\N	\N	\N	2026-04-03 00:51:40.309371
1372	2	login	user	2	\N	\N	\N	2026-04-03 00:57:29.266227
1373	2	login	user	2	\N	\N	\N	2026-04-03 01:06:13.18828
1374	2	login	user	2	\N	\N	\N	2026-04-03 01:08:17.264328
1375	2	login	user	2	\N	\N	\N	2026-04-03 01:18:17.12505
1376	2	login	user	2	\N	\N	\N	2026-04-03 01:21:08.380044
1377	2	login	user	2	\N	\N	\N	2026-04-03 01:25:30.353357
1378	2	login	user	2	\N	\N	\N	2026-04-03 01:28:41.01932
1379	2	login	user	2	\N	\N	\N	2026-04-03 02:13:32.897597
1380	2	login	user	2	\N	\N	\N	2026-04-03 02:48:32.365156
1381	2	login	user	2	\N	\N	\N	2026-04-03 03:06:45.430212
1382	2	login	user	2	\N	\N	\N	2026-04-03 03:08:46.211824
1383	2	login	user	2	\N	\N	\N	2026-04-03 03:55:37.650992
1384	2	login	user	2	\N	\N	\N	2026-04-03 04:12:53.851778
1385	2	login	user	2	\N	\N	\N	2026-04-03 04:14:34.96596
1386	2	login	user	2	\N	\N	\N	2026-04-03 04:36:54.332715
1387	2	login	user	2	\N	\N	\N	2026-04-03 06:25:22.780429
1388	2	login	user	2	\N	\N	\N	2026-04-03 06:26:27.931145
1389	2	login	user	2	\N	\N	\N	2026-04-03 06:26:55.915178
1390	2	login	user	2	\N	\N	\N	2026-04-03 06:27:58.195945
1391	2	login	user	2	\N	\N	\N	2026-04-03 07:13:26.235378
1392	2	login	user	2	\N	\N	\N	2026-04-03 07:53:58.374556
1393	2	login	user	2	\N	\N	\N	2026-04-03 07:54:08.615342
1394	2	login	user	2	\N	\N	\N	2026-04-03 08:34:34.052121
1395	2	login	user	2	\N	\N	\N	2026-04-04 01:32:20.738084
1396	2	login	user	2	\N	\N	\N	2026-04-04 02:30:33.328186
1397	2	login	user	2	\N	\N	\N	2026-04-04 02:46:47.041322
1398	2	login	user	2	\N	\N	\N	2026-04-04 03:18:14.419728
1399	2	login	user	2	\N	\N	\N	2026-04-04 03:26:08.351607
1400	2	login	user	2	\N	\N	\N	2026-04-04 09:48:22.122865
1401	2	login	user	2	\N	\N	\N	2026-04-04 09:50:17.328027
1402	2	login	user	2	\N	\N	\N	2026-04-04 09:51:18.416962
1403	2	login	user	2	\N	\N	\N	2026-04-04 10:45:42.612786
1404	2	login	user	2	\N	\N	\N	2026-04-04 13:38:29.000227
1405	2	login	user	2	\N	\N	\N	2026-04-04 14:05:47.675679
1406	2	login	user	2	\N	\N	\N	2026-04-05 03:58:03.332495
1407	2	login	user	2	\N	\N	\N	2026-04-05 04:13:19.78033
1408	2	login	user	2	\N	\N	\N	2026-04-05 04:18:33.950716
1409	2	login	user	2	\N	\N	\N	2026-04-05 04:24:18.462947
1410	2	login	user	2	\N	\N	\N	2026-04-05 04:31:27.95448
1411	2	login	user	2	\N	\N	\N	2026-04-05 04:37:02.417085
1412	2	login	user	2	\N	\N	\N	2026-04-05 04:45:47.983809
1413	2	login	user	2	\N	\N	\N	2026-04-05 05:20:49.300474
1414	2	login	user	2	\N	\N	\N	2026-04-05 05:22:45.459633
1415	2	login	user	2	\N	\N	\N	2026-04-05 05:26:24.099171
1416	2	login	user	2	\N	\N	\N	2026-04-05 05:35:42.691936
1417	2	login	user	2	\N	\N	\N	2026-04-05 05:37:02.163158
1418	2	login	user	2	\N	\N	\N	2026-04-05 05:40:49.652184
1419	2	login	user	2	\N	\N	\N	2026-04-05 06:33:20.968789
1420	2	login	user	2	\N	\N	\N	2026-04-05 06:36:46.319979
1421	2	login	user	2	\N	\N	\N	2026-04-05 06:41:15.419103
1422	2	login	user	2	\N	\N	\N	2026-04-05 06:56:52.456008
1423	2	login	user	2	\N	\N	\N	2026-04-05 06:59:56.57088
1424	2	login	user	2	\N	\N	\N	2026-04-05 07:05:04.229625
1425	2	login	user	2	\N	\N	\N	2026-04-05 11:32:04.932087
1426	2	login	user	2	\N	\N	\N	2026-04-05 11:52:36.548954
1427	2	login	user	2	\N	\N	\N	2026-04-05 12:11:00.101938
1428	2	login	user	2	\N	\N	\N	2026-04-05 12:49:32.569365
1429	2	login	user	2	\N	\N	\N	2026-04-05 12:54:20.093444
1430	2	login	user	2	\N	\N	\N	2026-04-05 14:34:42.49435
1431	2	login	user	2	\N	\N	\N	2026-04-05 14:40:14.665961
1432	2	login	user	2	\N	\N	\N	2026-04-05 14:48:35.726628
1433	2	login	user	2	\N	\N	\N	2026-04-05 15:00:50.096264
1434	2	login	user	2	\N	\N	\N	2026-04-05 15:04:42.906844
1435	2	login	user	2	\N	\N	\N	2026-04-05 15:13:26.009495
1436	2	login	user	2	\N	\N	\N	2026-04-06 00:19:49.336002
1437	2	login	user	2	\N	\N	\N	2026-04-06 00:25:37.172149
1438	2	login	user	2	\N	\N	\N	2026-04-06 00:36:26.668956
1439	2	login	user	2	\N	\N	\N	2026-04-06 01:01:13.698562
1440	2	login	user	2	\N	\N	\N	2026-04-06 01:02:30.694968
1441	2	login	user	2	\N	\N	\N	2026-04-06 01:04:50.795442
1442	2	login	user	2	\N	\N	\N	2026-04-06 01:12:48.032086
1443	2	login	user	2	\N	\N	\N	2026-04-06 01:26:12.032341
1444	2	login	user	2	\N	\N	\N	2026-04-06 01:40:51.177985
1445	2	login	user	2	\N	\N	\N	2026-04-06 01:54:50.988661
1446	2	login	user	2	\N	\N	\N	2026-04-06 02:00:44.282854
1447	2	login	user	2	\N	\N	\N	2026-04-06 02:40:00.829495
1448	2	login	user	2	\N	\N	\N	2026-04-06 02:49:14.144051
1449	2	login	user	2	\N	\N	\N	2026-04-06 02:54:56.528205
1450	2	login	user	2	\N	\N	\N	2026-04-06 03:12:49.28798
1451	2	login	user	2	\N	\N	\N	2026-04-06 04:36:01.771633
1452	2	login	user	2	\N	\N	\N	2026-04-06 04:55:20.521364
1453	\N	create_item	item	927	\N	{"name": "Калибр-кольцо М30*1,5 7h ПР (инструмент ТЦ),", "item_id": "13035"}	\N	2026-04-06 04:56:14.58928
1454	\N	create_item	item	928	\N	{"name": "Калибр-кольцо М8*1,25 7h ПР (инструмент ТЦ),", "item_id": "13034"}	\N	2026-04-06 04:56:14.593976
1455	2	login	user	2	\N	\N	\N	2026-04-06 05:11:54.253219
1456	2	login	user	2	\N	\N	\N	2026-04-06 06:23:13.965813
1457	2	login	user	2	\N	\N	\N	2026-04-06 06:54:54.885208
1458	2	login	user	2	\N	\N	\N	2026-04-06 07:37:54.900438
1459	2	login	user	2	\N	\N	\N	2026-04-06 08:03:12.735514
1460	2	login	user	2	\N	\N	\N	2026-04-06 08:27:21.703069
1461	2	login	user	2	\N	\N	\N	2026-04-06 08:40:29.515716
1462	2	login	user	2	\N	\N	\N	2026-04-06 14:29:20.906383
1463	2	login	user	2	\N	\N	\N	2026-04-06 14:47:05.170944
1464	2	login	user	2	\N	\N	\N	2026-04-06 14:54:06.674834
1465	2	login	user	2	\N	\N	\N	2026-04-06 15:17:32.448456
1466	2	logout	user	2	\N	\N	\N	2026-04-06 15:18:44.646288
1469	\N	create_user	user	9	\N	{"role": "user", "username": "Братушкин Андрей"}	\N	2026-04-06 15:19:49.154811
1476	2	login	user	2	\N	\N	\N	2026-04-07 00:12:37.769846
1477	\N	delete_user	user	9	{"username": "Братушкин Андрей"}	\N	\N	2026-04-07 00:12:53.461483
1478	2	login	user	2	\N	\N	\N	2026-04-07 00:16:39.970972
1479	2	logout	user	2	\N	\N	\N	2026-04-07 00:16:58.478359
1486	2	login	user	2	\N	\N	\N	2026-04-07 01:21:28.484447
1488	2	login	user	2	\N	\N	\N	2026-04-07 01:30:42.855387
1491	2	login	user	2	\N	\N	\N	2026-04-07 02:27:31.64849
1493	2	login	user	2	\N	\N	\N	2026-04-07 02:34:21.600311
1494	\N	expense_item	item	349	{"quantity": 8}	{"quantity": 7}	\N	2026-04-07 02:34:35.916652
1495	2	login	user	2	\N	\N	\N	2026-04-07 02:43:01.631925
1497	2	login	user	2	\N	\N	\N	2026-04-07 04:22:37.598035
1499	2	login	user	2	\N	\N	\N	2026-04-07 04:23:08.948045
1500	2	login	user	2	\N	\N	\N	2026-04-07 04:31:49.921805
1502	\N	expense_item	item	349	{"quantity": 7}	{"quantity": 6}	\N	2026-04-07 04:32:24.915904
1505	\N	income_item	item	349	{"quantity": 6}	{"quantity": 8}	\N	2026-04-07 05:06:40.783194
1506	\N	income_item	item	349	{"quantity": 8}	{"quantity": 10}	\N	2026-04-07 05:06:47.231745
1507	\N	income_item	item	349	{"quantity": 10}	{"quantity": 12}	\N	2026-04-07 05:06:47.981392
1508	\N	income_item	item	349	{"quantity": 12}	{"quantity": 14}	\N	2026-04-07 05:06:57.714491
1509	\N	income_item	item	349	{"quantity": 14}	{"quantity": 16}	\N	2026-04-07 05:07:00.380425
1510	\N	income_item	item	349	{"quantity": 16}	{"quantity": 18}	\N	2026-04-07 05:08:07.014729
1512	2	login	user	2	\N	\N	\N	2026-04-07 05:14:19.193014
1513	\N	expense_item	item	349	{"quantity": 8}	{"quantity": 7}	\N	2026-04-07 05:15:41.768882
1517	\N	income_item	item	349	{"quantity": 7}	{"quantity": 8}	\N	2026-04-07 05:30:05.360096
1518	2	login	user	2	\N	\N	\N	2026-04-07 05:30:13.054971
1520	\N	expense_item	item	349	{"quantity": 8}	{"quantity": 7}	\N	2026-04-07 05:32:41.844829
1522	2	login	user	2	\N	\N	\N	2026-04-07 05:37:20.405463
1524	\N	income_item	item	349	{"quantity": 7}	{"quantity": 8}	\N	2026-04-07 05:41:14.350849
1526	2	login	user	2	\N	\N	\N	2026-04-07 05:47:25.58338
1527	\N	expense_item	item	349	{"quantity": 8}	{"quantity": 7}	\N	2026-04-07 05:48:15.469598
1528	\N	income_item	item	349	{"quantity": 7}	{"quantity": 8}	\N	2026-04-07 05:48:22.735622
1531	\N	expense_item	item	349	{"quantity": 8}	{"quantity": 7}	\N	2026-04-07 06:11:41.459246
1532	\N	income_item	item	349	{"quantity": 7}	{"quantity": 8}	\N	2026-04-07 06:11:45.242443
1534	\N	expense_item	item	642	{"quantity": 1}	{"quantity": 0}	\N	2026-04-07 06:21:02.264866
1535	\N	income_item	item	642	{"quantity": 0}	{"quantity": 1}	\N	2026-04-07 06:21:04.895633
1537	\N	expense_item	item	789	{"quantity": 2}	{"quantity": 1}	\N	2026-04-07 06:22:28.663823
1538	\N	income_item	item	789	{"quantity": 1}	{"quantity": 2}	\N	2026-04-07 06:22:33.079595
1540	\N	expense_item	item	396	{"quantity": 1}	{"quantity": 0}	\N	2026-04-07 06:25:23.532161
1541	\N	income_item	item	396	{"quantity": 0}	{"quantity": 1}	\N	2026-04-07 06:25:28.298306
1543	\N	income_item	item	349	{"quantity": 8}	{"quantity": 9}	\N	2026-04-07 06:28:35.842975
1544	\N	income_item	item	789	{"quantity": 2}	{"quantity": 3}	\N	2026-04-07 06:28:38.188402
1545	\N	income_item	item	642	{"quantity": 1}	{"quantity": 2}	\N	2026-04-07 06:28:39.921037
1546	\N	income_item	item	396	{"quantity": 1}	{"quantity": 2}	\N	2026-04-07 06:28:41.538296
1551	2	login	user	2	\N	\N	\N	2026-04-07 07:14:07.28397
1552	2	logout	user	2	\N	\N	\N	2026-04-07 07:15:41.927406
1553	2	login	user	2	\N	\N	\N	2026-04-07 07:27:58.782668
1554	2	login	user	2	\N	\N	\N	2026-04-07 07:54:32.054121
1556	\N	expense_item	item	349	{"quantity": 9}	{"quantity": 8}	\N	2026-04-07 08:06:16.338508
1557	\N	income_item	item	349	{"quantity": 8}	{"quantity": 9}	\N	2026-04-07 08:06:21.010232
1558	\N	income_item	item	349	{"quantity": 9}	{"quantity": 10}	\N	2026-04-07 08:06:24.459934
1560	2	login	user	2	\N	\N	\N	2026-04-07 08:26:18.303681
1561	2	logout	user	2	\N	\N	\N	2026-04-07 08:32:10.078631
1562	\N	create_user	user	10	\N	{"role": "user", "username": "Пушкова Оксана"}	\N	2026-04-07 08:32:38.128611
1563	2	login	user	2	\N	\N	\N	2026-04-07 08:32:49.24508
1564	2	login	user	2	\N	\N	\N	2026-04-07 08:34:27.535372
1565	2	login	user	2	\N	\N	\N	2026-04-07 08:43:06.720164
1566	\N	update_workstations	user	10	{"workstations": "[\\"\\\\u0422\\\\u043e\\\\u043a\\\\u0430\\\\u0440\\\\u043d\\\\u044b\\\\u0439 ST16A25\\"]"}	{"workstations": null}	\N	2026-04-07 08:43:30.501594
1567	\N	update_user_screen_permissions	user	10	{"screen_permissions": null}	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"calendar\\", \\"planner\\", \\"my_page\\"]"}	\N	2026-04-07 08:43:30.505505
1568	2	logout	user	2	\N	\N	\N	2026-04-07 08:43:35.007372
1569	10	login	user	10	\N	\N	\N	2026-04-07 08:43:47.105596
1571	2	login	user	2	\N	\N	\N	2026-04-07 08:56:16.033862
1575	\N	expense_item	item	789	{"quantity": 3}	{"quantity": 2}	\N	2026-04-07 12:59:11.768968
1582	2	login	user	2	\N	\N	\N	2026-04-07 15:21:40.265056
1583	2	login	user	2	\N	\N	\N	2026-04-08 00:10:02.889081
1584	2	login	user	2	\N	\N	\N	2026-04-08 00:22:56.614155
1585	2	login	user	2	\N	\N	\N	2026-04-08 01:07:38.850789
1586	10	login	user	10	\N	\N	\N	2026-04-08 01:14:33.706767
1587	2	login	user	2	\N	\N	\N	2026-04-08 01:31:44.273193
1589	\N	income_item	item	349	{"quantity": 10}	{"quantity": 25}	\N	2026-04-08 01:44:35.945446
1590	10	login	user	10	\N	\N	\N	2026-04-08 01:50:11.728225
1591	2	login	user	2	\N	\N	\N	2026-04-08 01:52:42.589053
1592	2	logout	user	2	\N	\N	\N	2026-04-08 02:25:43.41473
1595	10	login	user	10	\N	\N	\N	2026-04-08 03:03:12.439712
1604	2	login	user	2	\N	\N	\N	2026-04-08 04:35:10.170946
1605	2	login	user	2	\N	\N	\N	2026-04-08 04:41:28.183619
1606	2	login	user	2	\N	\N	\N	2026-04-08 04:57:47.199624
1607	2	login	user	2	\N	\N	\N	2026-04-08 05:17:56.557584
1608	2	login	user	2	\N	\N	\N	2026-04-08 05:25:49.480758
1609	2	login	user	2	\N	\N	\N	2026-04-08 05:28:55.843585
1612	2	logout	user	2	\N	\N	\N	2026-04-08 05:51:48.749244
1614	\N	expense_item	item	349	{"quantity": 25}	{"quantity": 24}	\N	2026-04-08 05:52:12.415333
1616	2	login	user	2	\N	\N	\N	2026-04-08 05:54:49.786241
1617	2	login	user	2	\N	\N	\N	2026-04-08 06:09:20.350704
1618	2	login	user	2	\N	\N	\N	2026-04-08 06:14:23.441179
1619	2	login	user	2	\N	\N	\N	2026-04-08 06:28:36.154047
1620	2	login	user	2	\N	\N	\N	2026-04-08 06:30:30.002306
1621	2	login	user	2	\N	\N	\N	2026-04-08 06:32:28.800652
1622	2	login	user	2	\N	\N	\N	2026-04-08 06:41:26.221044
1623	2	login	user	2	\N	\N	\N	2026-04-08 06:49:07.877208
1624	2	login	user	2	\N	\N	\N	2026-04-08 07:26:33.426234
1625	2	login	user	2	\N	\N	\N	2026-04-08 07:33:14.02428
1626	2	login	user	2	\N	\N	\N	2026-04-08 07:36:42.960287
1627	2	login	user	2	\N	\N	\N	2026-04-08 07:39:35.067956
1628	2	login	user	2	\N	\N	\N	2026-04-08 07:42:54.118562
1629	2	login	user	2	\N	\N	\N	2026-04-08 07:47:23.575187
1630	2	login	user	2	\N	\N	\N	2026-04-08 07:56:17.222092
1631	2	login	user	2	\N	\N	\N	2026-04-08 08:00:54.488038
1632	2	login	user	2	\N	\N	\N	2026-04-08 08:05:59.800496
1633	2	login	user	2	\N	\N	\N	2026-04-08 08:14:22.76123
1634	2	login	user	2	\N	\N	\N	2026-04-08 08:16:48.163952
1635	2	login	user	2	\N	\N	\N	2026-04-08 08:45:10.344955
1636	2	login	user	2	\N	\N	\N	2026-04-08 13:19:26.818778
1637	2	login	user	2	\N	\N	\N	2026-04-08 13:25:00.672376
1638	10	login	user	10	\N	\N	\N	2026-04-08 13:36:03.707925
1639	10	logout	user	10	\N	\N	\N	2026-04-08 13:36:10.508385
1640	2	login	user	2	\N	\N	\N	2026-04-08 13:36:16.407629
1641	2	login	user	2	\N	\N	\N	2026-04-08 13:45:22.070236
1642	\N	update_workstations	user	8	{"workstations": null}	{"workstations": null}	\N	2026-04-08 13:45:32.960246
1643	\N	update_user_screen_permissions	user	8	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"workshop_ops\\", \\"reports\\", \\"production_plan\\", \\"planner\\"]"}	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"]"}	\N	2026-04-08 13:45:32.964906
1644	\N	update_user_route_view_mode	user	8	{"route_view_mode": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-08 13:45:32.967919
1645	2	logout	user	2	\N	\N	\N	2026-04-08 13:45:35.961724
1646	8	login	user	8	\N	\N	\N	2026-04-08 13:46:10.201691
1647	2	login	user	2	\N	\N	\N	2026-04-08 14:06:52.937201
1650	2	login	user	2	\N	\N	\N	2026-04-08 14:50:21.449462
1651	2	login	user	2	\N	\N	\N	2026-04-08 14:57:04.702993
1653	2	login	user	2	\N	\N	\N	2026-04-08 15:22:08.165485
1654	2	login	user	2	\N	\N	\N	2026-04-09 01:12:12.896828
1655	2	login	user	2	\N	\N	\N	2026-04-09 01:12:32.583577
1656	2	login	user	2	\N	\N	\N	2026-04-09 01:15:16.197416
1657	2	login	user	2	\N	\N	\N	2026-04-09 01:15:18.124036
1658	2	login	user	2	\N	\N	\N	2026-04-09 01:15:30.390717
1659	2	login	user	2	\N	\N	\N	2026-04-09 01:19:11.012073
1660	2	login	user	2	\N	\N	\N	2026-04-09 01:21:41.976813
1661	2	login	user	2	\N	\N	\N	2026-04-09 01:33:06.53229
1662	2	login	user	2	\N	\N	\N	2026-04-09 07:08:15.822853
1663	2	login	user	2	\N	\N	\N	2026-04-09 12:43:25.646936
1664	2	login	user	2	\N	\N	\N	2026-04-09 12:50:45.210688
1665	2	login	user	2	\N	\N	\N	2026-04-09 13:00:53.923019
1666	2	login	user	2	\N	\N	\N	2026-04-10 01:50:11.523347
1667	2	login	user	2	\N	\N	\N	2026-04-10 06:03:56.386067
1668	2	login	user	2	\N	\N	\N	2026-04-10 23:49:17.858005
1669	2	login	user	2	\N	\N	\N	2026-04-11 00:28:08.48411
1670	2	login	user	2	\N	\N	\N	2026-04-11 02:11:12.977209
1671	\N	update_workstations	user	7	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	{"workstations": ""}	\N	2026-04-13 14:07:32.609728
1672	\N	update_user_route_view_mode	user	7	{"route_view_mode": "[\\"dashboard\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-13 14:07:32.618498
1673	\N	update_workstations	user	7	{"workstations": ""}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-13 14:22:11.141325
1674	\N	update_user_route_view_mode	user	7	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-13 14:22:11.146063
1675	\N	update_user_screen_permissions	user	7	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-13 14:22:11.148638
1676	\N	update_workstations	user	8	{"workstations": null}	{"workstations": "[]"}	\N	2026-04-13 14:22:48.190135
1763	2	login	user	2	\N	\N	\N	2026-04-16 05:53:05.586359
1765	2	login	user	2	\N	\N	\N	2026-04-16 08:36:37.518682
1677	\N	update_user_route_view_mode	user	8	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-13 14:22:48.194098
1678	\N	update_user_screen_permissions	user	8	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"users\\", \\"calendar\\", \\"gantt\\", \\"reports\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-13 14:22:48.197962
1679	2	login	user	2	\N	\N	\N	2026-04-14 00:05:15.796105
1680	2	login	user	2	\N	\N	\N	2026-04-14 00:18:37.578617
1681	\N	update_workstations	user	10	{"workstations": null}	{"workstations": "[]"}	\N	2026-04-14 02:10:21.647147
1682	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"calendar\\", \\"planner\\", \\"my_page\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"calendar\\", \\"planner\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:10:21.653582
1683	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"calendar\\", \\"planner\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:10:21.65618
1684	10	login	user	10	\N	\N	\N	2026-04-14 02:10:51.176269
1685	2	login	user	2	\N	\N	\N	2026-04-14 02:11:08.382671
1686	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:11:19.180122
1687	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:11:19.183789
1688	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:11:19.189458
1689	10	login	user	10	\N	\N	\N	2026-04-14 02:11:25.274405
1690	2	login	user	2	\N	\N	\N	2026-04-14 02:11:42.726524
1691	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:11:53.279547
1692	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:11:53.282495
1693	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:11:53.286363
1694	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:16:38.669794
1695	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:16:38.673465
1696	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:16:38.675417
1697	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:16:46.505482
1698	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:16:46.509437
1699	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:16:46.512331
1700	10	login	user	10	\N	\N	\N	2026-04-14 02:16:52.180698
1701	2	login	user	2	\N	\N	\N	2026-04-14 02:29:26.961891
1702	10	login	user	10	\N	\N	\N	2026-04-14 02:33:28.644271
1703	2	login	user	2	\N	\N	\N	2026-04-14 02:33:38.410793
1704	10	login	user	10	\N	\N	\N	2026-04-14 02:38:54.993857
1705	2	login	user	2	\N	\N	\N	2026-04-14 02:42:29.122968
1706	\N	update_workstations	user	8	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:42:48.341453
1707	\N	update_user_route_view_mode	user	8	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:42:48.34393
1708	\N	update_user_screen_permissions	user	8	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	\N	2026-04-14 02:42:48.347159
1709	\N	update_workstations	user	2	{"workstations": null}	{"workstations": "[]"}	\N	2026-04-14 02:42:58.893982
1710	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"users\\", \\"calendar\\", \\"scanner\\", \\"gantt\\", \\"workshop_ops\\", \\"reports\\", \\"production_plan\\", \\"planner\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"users\\", \\"calendar\\", \\"scanner\\", \\"gantt\\", \\"workshop_ops\\", \\"reports\\", \\"production_plan\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:42:58.897003
1766	\N	create_user	user	11	\N	{"role": "user", "login": "Максимов", "username": "Александр"}	\N	2026-04-17 00:47:38.740895
1767	11	login	user	11	\N	\N	\N	2026-04-17 00:47:45.028596
1768	2	login	user	2	\N	\N	\N	2026-04-17 00:47:55.349932
1835	2	login	user	2	\N	\N	\N	2026-04-22 06:14:19.675535
1711	\N	update_user_screen_permissions	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"details\\", \\"routes\\", \\"plan\\", \\"inventory\\", \\"transactions\\", \\"workshop_inventory\\", \\"planning_settings\\", \\"users\\", \\"calendar\\", \\"scanner\\", \\"gantt\\", \\"workshop_ops\\", \\"reports\\", \\"production_plan\\", \\"planner\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"my_page\\"]"}	\N	2026-04-14 02:42:58.900788
1712	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:43:16.259998
1713	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"my_page\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:43:16.263977
1714	\N	update_user_screen_permissions	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"]"}	\N	2026-04-14 02:43:16.26761
1715	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:44:06.453922
1716	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:44:06.45859
1717	\N	update_user_screen_permissions	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"]"}	\N	2026-04-14 02:44:06.461506
1718	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-14 02:52:40.288305
1719	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:52:40.293073
1720	\N	update_user_screen_permissions	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"]"}	\N	2026-04-14 02:52:40.29667
1721	2	login	user	2	\N	\N	\N	2026-04-14 02:53:00.060948
1723	2	login	user	2	\N	\N	\N	2026-04-14 02:57:52.678241
1724	\N	update_workstations	user	7	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-14 02:57:58.71565
1725	\N	update_user_route_view_mode	user	7	{"route_view_mode": "[]"}	{"route_view_mode": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-14 02:57:58.718263
1726	\N	update_user_screen_permissions	user	7	{"screen_permissions": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-14 02:57:58.720685
1729	2	login	user	2	\N	\N	\N	2026-04-14 03:04:44.896067
1730	10	login	user	10	\N	\N	\N	2026-04-14 03:09:25.667686
1731	10	login	user	10	\N	\N	\N	2026-04-14 03:09:28.221022
1732	10	login	user	10	\N	\N	\N	2026-04-14 03:12:59.76006
1733	2	login	user	2	\N	\N	\N	2026-04-14 05:25:34.392901
1734	10	login	user	10	\N	\N	\N	2026-04-14 08:37:29.832655
1735	2	login	user	2	\N	\N	\N	2026-04-14 08:37:39.877788
1738	\N	update_workstations	user	7	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-15 01:47:36.925813
1739	\N	update_user_route_view_mode	user	7	{"route_view_mode": "[]"}	{"route_view_mode": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-15 01:47:36.929611
1740	\N	update_user_screen_permissions	user	7	{"screen_permissions": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-15 01:47:36.932006
1750	2	login	user	2	\N	\N	\N	2026-04-15 04:20:10.076846
1751	2	login	user	2	\N	\N	\N	2026-04-15 04:20:52.962623
1752	2	login	user	2	\N	\N	\N	2026-04-15 04:22:36.642664
1753	2	login	user	2	\N	\N	\N	2026-04-15 04:29:52.69706
1757	2	login	user	2	\N	\N	\N	2026-04-16 04:57:33.902851
1760	2	login	user	2	\N	\N	\N	2026-04-16 05:38:26.66787
1769	\N	update_workstations	user	11	{"workstations": null}	{"workstations": "[]"}	\N	2026-04-17 00:50:17.531512
1770	\N	update_user_route_view_mode	user	11	{"route_view_mode": null}	{"route_view_mode": "{\\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-17 00:50:17.538685
1771	\N	update_user_screen_permissions	user	11	{"screen_permissions": "{\\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-17 00:50:17.542367
1772	\N	update_workstations	user	11	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-17 00:50:42.51907
1773	\N	update_user_route_view_mode	user	11	{"route_view_mode": "[]"}	{"route_view_mode": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-17 00:50:42.521806
1774	\N	update_user_screen_permissions	user	11	{"screen_permissions": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-17 00:50:42.524557
1775	\N	update_workstations	user	11	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-17 00:55:28.898205
1776	\N	update_user_route_view_mode	user	11	{"route_view_mode": "[]"}	{"route_view_mode": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-17 00:55:28.901577
1777	\N	update_user_screen_permissions	user	11	{"screen_permissions": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-17 00:55:28.904852
1778	\N	update_workstations	user	11	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-17 01:03:36.7559
1779	\N	update_user_route_view_mode	user	11	{"route_view_mode": "[]"}	{"route_view_mode": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-17 01:03:36.760795
1780	\N	update_user_screen_permissions	user	11	{"screen_permissions": "{\\"screens\\": [], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-17 01:03:36.763531
1781	11	login	user	11	\N	\N	\N	2026-04-17 01:05:01.836758
1783	2	login	user	2	\N	\N	\N	2026-04-17 01:31:26.958558
1785	2	login	user	2	\N	\N	\N	2026-04-17 01:35:07.993597
1786	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-17 01:35:21.292358
1787	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-17 01:35:21.296593
1788	\N	update_user_screen_permissions	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"]"}	\N	2026-04-17 01:35:21.299185
1789	2	login	user	2	\N	\N	\N	2026-04-17 01:48:46.362427
1791	2	login	user	2	\N	\N	\N	2026-04-17 03:38:05.795187
1792	2	login	user	2	\N	\N	\N	2026-04-17 03:52:28.215133
1793	2	login	user	2	\N	\N	\N	2026-04-17 06:59:44.235704
1795	2	login	user	2	\N	\N	\N	2026-04-19 13:11:30.542304
1797	\N	expense_item	item	647	{"quantity": 5}	{"quantity": 4}	\N	2026-04-20 00:17:32.811356
1798	\N	income_item	item	789	{"quantity": 2}	{"quantity": 3}	\N	2026-04-20 00:32:44.119444
1799	\N	income_item	item	349	{"quantity": 24}	{"quantity": 26}	\N	2026-04-20 00:32:53.011046
1800	\N	income_item	item	647	{"quantity": 4}	{"quantity": 5}	\N	2026-04-20 00:33:01.126112
1801	\N	expense_item	item	349	{"quantity": 26}	{"quantity": 25}	\N	2026-04-20 00:33:17.663472
1802	\N	expense_item	item	647	{"quantity": 5}	{"quantity": 4}	\N	2026-04-20 01:13:26.611857
1803	\N	expense_item	item	650	{"quantity": 10}	{"quantity": 9}	\N	2026-04-20 01:13:38.975981
1804	\N	expense_item	item	651	{"quantity": 1}	{"quantity": 0}	\N	2026-04-20 01:13:50.058776
1805	2	login	user	2	\N	\N	\N	2026-04-21 05:07:35.702876
1806	11	login	user	11	\N	\N	\N	2026-04-21 05:17:45.825845
1807	2	login	user	2	\N	\N	\N	2026-04-21 05:18:22.618241
1809	11	login	user	11	\N	\N	\N	2026-04-22 00:12:22.848683
1810	11	login	user	11	\N	\N	\N	2026-04-22 02:13:01.788749
1811	\N	toggle_user_active	user	7	{"is_active": true}	{"is_active": false}	\N	2026-04-22 04:27:25.55374
1812	\N	delete_user	user	7	{"username": "Братушкин Роман"}	\N	\N	2026-04-22 04:32:18.851254
1813	\N	create_user	user	12	\N	{"role": "user", "login": "r.brstushkin", "username": "Роман"}	\N	2026-04-22 04:32:57.549275
1815	\N	update_workstations	user	12	{"workstations": null}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-22 04:33:41.91271
1816	\N	update_user_route_view_mode	user	12	{"route_view_mode": null}	{"route_view_mode": "{\\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-22 04:33:41.916829
1817	\N	update_user_screen_permissions	user	12	{"screen_permissions": "{\\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-22 04:33:41.919181
1819	\N	delete_user	user	12	{"username": "Роман"}	\N	\N	2026-04-22 04:40:16.164743
1820	\N	create_user	user	13	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 04:41:04.74065
1822	\N	delete_user	user	13	{"username": "Роман"}	\N	\N	2026-04-22 04:41:45.20482
1823	\N	create_user	user	14	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 04:46:20.952752
1824	\N	delete_user	user	14	{"username": "Роман"}	\N	\N	2026-04-22 05:26:09.426914
1825	\N	create_user	user	15	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 05:26:34.201883
1827	\N	delete_user	user	15	{"username": "Роман"}	\N	\N	2026-04-22 05:41:58.604407
1828	\N	create_user	user	16	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 05:42:48.840147
1829	\N	delete_user	user	16	{"username": "Роман"}	\N	\N	2026-04-22 05:43:33.485786
1830	\N	create_user	user	17	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 05:45:33.843953
1831	\N	delete_user	user	17	{"username": "Роман"}	\N	\N	2026-04-22 05:46:00.176434
1832	\N	create_user	user	18	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 06:13:50.268569
1833	10	login	user	10	\N	\N	\N	2026-04-22 06:13:56.337307
1837	2	login	user	2	\N	\N	\N	2026-04-22 06:22:50.302859
1838	\N	update_workstations	user	18	{"workstations": null}	{"workstations": "[\\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21161\\", \\"\\\\u0424\\\\u0440\\\\u0435\\\\u0437\\\\u0435\\\\u0440\\\\u043d\\\\u044b\\\\u0439 IMU-5x400_\\\\u21162\\"]"}	\N	2026-04-22 06:23:00.989366
1839	\N	update_user_route_view_mode	user	18	{"route_view_mode": null}	{"route_view_mode": "{\\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-22 06:23:00.993464
1840	\N	update_user_screen_permissions	user	18	{"screen_permissions": "{\\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[]"}	\N	2026-04-22 06:23:00.996134
1841	\N	delete_user	user	18	{"username": "Роман"}	\N	\N	2026-04-22 07:01:20.974201
1842	\N	create_user	user	19	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 07:03:54.392885
1843	\N	delete_user	user	19	{"username": "Роман"}	\N	\N	2026-04-22 07:04:15.73007
1844	\N	create_user	user	20	\N	{"role": "user", "login": "r.bratushkin", "username": "Роман"}	\N	2026-04-22 07:05:00.749043
1845	\N	delete_user	user	20	{"username": "Роман"}	\N	\N	2026-04-22 07:10:52.077996
1846	\N	create_user	user	21	\N	{"role": "user", "login": "r.bratushkin", "username": "Братушкин Роман"}	\N	2026-04-22 07:11:24.189606
1847	21	login	user	21	\N	\N	\N	2026-04-22 07:18:21.382447
1848	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-22 15:23:17.342054
1849	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-22 15:23:17.348831
1850	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	\N	2026-04-22 15:23:17.351253
1851	10	login	user	10	\N	\N	\N	2026-04-22 15:23:38.644955
1852	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-22 15:25:51.539126
1853	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-22 15:25:51.546103
1854	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	\N	2026-04-22 15:25:51.550671
1855	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-22 15:26:04.250095
1856	\N	update_user_route_view_mode	user	10	{"route_view_mode": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-22 15:26:04.255446
1857	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	\N	2026-04-22 15:26:04.259727
1858	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 00:30:49.094013
1859	\N	update_user_screen_permissions	user	10	{"screen_permissions": "[\\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"materials\\", \\"equipment\\"]"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 00:30:49.097283
1860	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 00:33:11.084151
1861	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\", \\"my_page\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 00:33:11.089766
1862	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 00:53:29.971454
1863	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 00:53:29.977652
1864	10	login	user	10	\N	\N	\N	2026-04-23 00:53:45.421233
1865	10	login	user	10	\N	\N	\N	2026-04-23 00:54:14.215058
1866	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 01:38:30.361566
1867	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 01:38:30.367171
1868	10	login	user	10	\N	\N	\N	2026-04-23 01:38:42.585976
1869	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 01:40:29.033788
1870	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 01:40:29.03925
1871	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 02:39:52.714044
1872	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 02:39:52.719807
1873	10	login	user	10	\N	\N	\N	2026-04-23 02:40:04.934532
1874	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 02:40:13.416613
1875	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 02:40:14.638216
1876	10	login	user	10	\N	\N	\N	2026-04-23 02:47:23.889113
1877	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 02:47:28.208938
1878	\N	update_user_route_view_mode	user	2	{"route_view_mode": "[\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"]"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 02:48:30.059325
1879	\N	update_user_route_view_mode	user	2	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"all\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 02:53:15.678226
1880	\N	update_user_route_view_mode	user	2	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 02:53:16.666346
1881	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 02:53:21.195242
1882	10	login	user	10	\N	\N	\N	2026-04-23 02:53:46.919686
1883	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 02:53:51.196244
1884	\N	update_user_route_view_mode	user	10	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"route_view_mode": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 02:53:51.854921
1885	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 03:00:27.453329
1886	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-23 03:00:27.45645
1887	10	login	user	10	\N	\N	\N	2026-04-23 03:03:01.111994
1888	21	login	user	21	\N	\N	\N	2026-04-23 03:12:08.409155
1889	11	login	user	11	\N	\N	\N	2026-04-23 03:12:39.514379
1890	10	login	user	10	\N	\N	\N	2026-04-23 04:18:57.179596
1891	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 04:19:25.341007
1892	\N	update_user_screen_permissions	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-23 04:19:25.344898
1893	\N	create_item	item	929	\N	{"name": "Сверло корпус UD30.SP07.240.W25", "item_id": "00000"}	\N	2026-04-23 04:44:17.529809
1894	10	login	user	10	\N	\N	\N	2026-04-23 05:03:13.062418
1895	10	login	user	10	\N	\N	\N	2026-04-23 05:03:14.296436
1896	10	login	user	10	\N	\N	\N	2026-04-23 05:28:56.854683
1897	10	login	user	10	\N	\N	\N	2026-04-23 07:23:13.471435
1898	\N	create_item	item	930	\N	{"name": "Сверло корпус UD30.SP07.240.W25", "item_id": "000000"}	\N	2026-04-23 07:28:58.177161
1899	10	login	user	10	\N	\N	\N	2026-04-23 08:24:14.970927
1900	2	login	user	2	\N	\N	\N	2026-04-23 13:04:18.616594
1901	10	login	user	10	\N	\N	\N	2026-04-23 13:23:49.22525
1902	2	login	user	2	\N	\N	\N	2026-04-23 13:24:23.767345
1903	10	login	user	10	\N	\N	\N	2026-04-23 14:09:01.114085
1904	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-23 14:37:58.314946
1905	10	login	user	10	\N	\N	\N	2026-04-23 14:38:08.78141
1906	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:26:08.963216
1907	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:36:33.904846
1908	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:37:31.258316
1909	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:37:47.3636
1910	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:37:54.881024
1911	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:50:07.749633
1912	\N	update_user_screen_permissions_dict	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"planner\\", \\"routes\\", \\"equipment\\", \\"users\\", \\"reports\\", \\"transactions\\", \\"import_export\\", \\"planning_settings\\", \\"workshop_inventory\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"workshop_inventory\\", \\"transactions\\", \\"details\\", \\"routes\\", \\"planning\\", \\"planning_calendar\\", \\"planning_gantt\\", \\"planning_settings\\", \\"materials\\", \\"equipment\\", \\"reports\\", \\"import_export\\", \\"users\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-24 00:50:07.756073
1913	\N	update_workstations	user	2	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 00:58:02.793998
1914	\N	update_user_screen_permissions_dict	user	2	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"workshop_inventory\\", \\"transactions\\", \\"details\\", \\"routes\\", \\"planning\\", \\"planning_calendar\\", \\"planning_gantt\\", \\"planning_settings\\", \\"materials\\", \\"equipment\\", \\"reports\\", \\"import_export\\", \\"users\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"workshop_inventory\\", \\"transactions\\", \\"details\\", \\"routes\\", \\"planning\\", \\"planning_calendar\\", \\"planning_gantt\\", \\"planning_settings\\", \\"materials\\", \\"equipment\\", \\"reports\\", \\"import_export\\", \\"users\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-24 00:58:02.799093
1915	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 01:02:01.480745
1916	\N	update_user_screen_permissions_dict	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-24 01:02:01.48652
1917	10	login	user	10	\N	\N	\N	2026-04-24 01:02:17.40948
1918	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 01:25:04.64985
1919	\N	update_user_screen_permissions_dict	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-24 01:25:04.653217
1920	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 01:25:14.974706
1921	\N	update_user_screen_permissions_dict	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	\N	2026-04-24 01:25:14.978614
1922	10	login	user	10	\N	\N	\N	2026-04-24 01:25:29.284982
1923	\N	update_workstations	user	10	{"workstations": "[]"}	{"workstations": "[]"}	\N	2026-04-24 01:28:50.002254
1924	\N	update_user_screen_permissions_dict	user	10	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"all\\"}"}	{"screen_permissions": "{\\"screens\\": [\\"dashboard\\", \\"inventory\\", \\"details\\", \\"routes\\", \\"planning_calendar\\", \\"materials\\"], \\"route_view_mode\\": \\"approved_only\\"}"}	\N	2026-04-24 01:28:50.007872
1925	11	login	user	11	\N	\N	\N	2026-04-24 01:29:47.765533
1926	21	login	user	21	\N	\N	\N	2026-04-24 01:33:49.557352
1927	10	login	user	10	\N	\N	\N	2026-04-24 01:53:48.238156
\.


--
-- Data for Name: batch_counter; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.batch_counter (id, prefix, last_number) FROM stdin;
2	П	0
1	Ш	17
\.


--
-- Data for Name: calendar_configs; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.calendar_configs (id, user_id, config_key, visible_equipment, equipment_order, panel_visible, created_at, updated_at) FROM stdin;
10	2	default	[57, 53, 54, 55, 56, 12, 13, 24, 25, 48, 49, 50, 27, 14, 5, 6, 16, 17, 28, 51, 52, 30, 2, 3, 4, 1, 21, 20, 33, 41, 40, 7, 15, 37, 36, 8, 38, 10, 19, 22, 39, 42, 9, 23, 34, 35, 18, 32, 31]	[27, 24, 25, 48, 49, 50, 28, 51, 52, 30, 36, 13, 57, 53, 54, 55, 56, 32, 18, 35, 7, 16, 17, 5, 6, 4, 2, 3, 10, 34, 31, 20, 19, 21, 22, 1, 23, 8, 12, 14, 15, 37, 38, 40, 42]	t	2026-03-19 08:47:39.86688	2026-04-23 05:54:26.669569
11	10	default	[57, 53, 54, 55, 56, 12, 13, 24, 25, 48, 49, 50, 27, 14, 5, 6, 16, 17, 28, 51, 52, 30, 2, 3, 4, 1, 21, 20, 33, 41, 40, 7, 15, 37, 36, 8, 38, 10, 19, 22, 39, 42, 9, 23, 34, 35, 18, 32, 31]	[27, 24, 25, 48, 49, 50, 28, 51, 52, 30, 36, 35, 13, 18, 32, 7, 16, 17, 5, 6, 4, 2, 3, 10, 34, 31, 20, 19, 21, 22, 1, 23, 8, 9, 12, 14, 15, 37, 38, 40, 42, 53, 54, 55, 56, 57]	t	2026-04-08 01:52:12.080113	2026-04-23 05:54:47.506555
\.


--
-- Data for Name: cooperatives; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.cooperatives (id, name, description, is_active) FROM stdin;
1	Энерпред	\N	1
2	Стальное звено	\N	1
3	Оргтехоснастка	\N	1
\.


--
-- Data for Name: detail_routes; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.detail_routes (id, detail_name, designation, material_instance_id, pdf_file, status, created_by, created_at, updated_at, quantity, pdf_path, pdf_data, length, diameter, preprocessing_data, version, approved, detail_id, app_id, lotzman_id, is_actual, dimension1, dimension2, parts_per_blank, waste_percent, preprocessing, primitive_form_id, prim_dim1, prim_dim2, prim_dim3, lot_size, file, change_indicator, volume, calculated_mass, blank_cost, manual_mass_input, material_cost, unit_cost, labor_cost, depreciation_cost, utility_cost, dimensions, preprocessing_dimensions, name) FROM stdin;
97	Крепление	L101.20.03.104	188	\N	черновик	admin	2026-04-22 14:44:49.208509	2026-04-22 23:09:04.117112	1	\N	\N	200	\N	{"preprocessing":true,"return_percent":0,"item_type":"detail","form_type":"Цилиндр","param_l":"195","param_d":"47"}	1.0	f	50	\N	\N	t	200	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
98	Втулка резьбовая	PO.BMEX.404.200.003	30	\N	active	Пушкова Оксана	2026-04-23 12:30:32.320009	2026-04-23 12:34:15.470649	1	\N	\N	\N	\N	{"preprocessing":false,"return_percent":0,"item_type":"detail"}	1	f	130	\N	\N	t	30	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
96	Втулка	L101.22.00.603	\N	\N	черновик	admin	2026-04-16 13:40:17.920049	2026-04-16 13:40:17.920049	1	\N	\N	\N	\N	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 0}	1.0	t	51	\N	\N	t	\N	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
87	Вилка большая	8.10.251	43	\N	черновик	admin	2026-04-11 19:07:03.490696	2026-04-22 04:32:18.866979	1	\N	\N	100	150	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 150}	1.0	f	\N	\N	\N	t	100	150	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
88	Фланец проходной 8.10.708	L101.10.05.601	18	\N	черновик	admin	2026-04-11 19:12:19.458988	2026-04-22 04:32:18.866981	1	\N	\N	150	\N	{"preprocessing":false,"return_percent":0,"item_type":"detail"}	1.0	f	\N	\N	\N	t	150	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
92	Фланец проходной 8.10.708	L101.10.05.601	18	\N	active	admin	2026-04-11 23:04:07.773676	2026-04-22 04:32:18.866982	1	\N	\N	\N	\N	{"preprocessing":false,"return_percent":0,"item_type":"detail"}	2	f	\N	\N	\N	t	150	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
93	Труба	CK-6.01.001	\N	\N	черновик	admin	2026-04-15 13:00:46.302402	2026-04-22 04:32:18.866983	1	\N	\N	100	\N	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 0}	1.0	t	\N	\N	\N	t	100	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
94	Труба	CK-6.01.001	\N	\N	active	admin	2026-04-16 08:49:18.272638	2026-04-22 04:32:18.866984	1	\N	\N	\N	\N	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 0}	2	t	\N	\N	\N	t	100	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
95	Труба	CK-6.01.001	\N	\N	active	admin	2026-04-16 08:49:35.845585	2026-04-22 04:32:18.866984	1	\N	\N	\N	\N	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 0}	3	t	\N	\N	\N	t	100	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
100	Кольцо	PO.BMEX.404.200.009	152	\N	черновик	Пушкова Оксана	2026-04-23 13:05:01.879818	2026-04-23 13:05:01.879818	1	\N	\N	200	\N	{"preprocessing": false, "return_percent": 0.0, "item_type": "detail", "width": 0}	1.0	t	131	\N	\N	t	200	\N	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
101	Кольцо стопорное	8.10.233	48	\N	черновик	Пушкова Оксана	2026-04-23 13:41:37.662762	2026-04-23 13:43:18.89013	10	\N	\N	100	100	{"preprocessing":false,"return_percent":0,"item_type":"detail"}	1.0	f	132	\N	\N	t	100	100	1	0	f	\N	\N	\N	\N	1	\N	f	\N	\N	\N	f	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: details; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.details (id, detail_id, lotzman_id, detail_type, designation, name, version, is_actual, drawing, correct_designation, creator_id, created_at) FROM stdin;
130	5b2a47fc-eb59-4e41-9e0a-6e007d733c24	\N	Деталь	PO.BMEX.404.200.003	Втулка резьбовая	1	t	\N	t	10	\N
6	bb1a6238	\N	Деталь	PO.8.10.083.001.001	Корпус конуса	1	t	\N	t	\N	2026-03-02 08:12:34
7	f7f8a342	\N	Деталь	PO.MECX.4H04C45.01.100.002	Шайба 15	1	t	ДСЕ_Files_/f7f8a342.Чертеж.032010.002 - Шайба 15.cdw	t	\N	2026-03-02 11:19:13
8	e47b18c4	\N	Деталь	PO.MECX.4H04C45.01.100.045-01	Оправка 45	1	t	ДСЕ_Files_/e47b18c4.Чертеж.032304.045-01 - Оправка 45.cdw	t	\N	2026-03-02 11:22:33
9	cb13326c	\N	Деталь	SO.8.10.271.000.101	Пуансон	1	t	\N	t	\N	2026-04-02 10:50:23
10	e4680235	\N	Деталь	SO.8.10.271.000.102	Прижим	1	t	\N	t	\N	2026-05-02 07:35:50
11	88dc6fd1	\N	Деталь	TR20.09.00.001	Проставка для раздатки	1	t	\N	t	\N	2026-05-02 08:31:12
12	1a8e861a	\N	Деталь	PO.8.10.083.001.002	Конус	1	t	\N	t	\N	2026-05-02 09:05:25
13	37a531df	\N	Деталь	PO.MECXXXXXXX.01.100.001	Оправка пирамида	1	t	\N	t	\N	2026-05-02 11:33:45
14	f5f1792c	\N	Деталь	L101.22.21.103	Рычаг	1	t	\N	t	\N	2026-05-02 15:06:57
15	d13bbf07	\N	Деталь	L101.22.21.104	Рычаг	1	t	\N	t	\N	2026-05-02 15:15:53
16	cdb8894b	\N	Деталь	S001.073.005	Штуцер	1	t	\N	t	\N	2026-05-02 15:23:07
17	0bdfc1f0	\N	Деталь	L101.52.12.002	Втулка крепления рамы отвала	1	t	\N	t	\N	2026-06-02 07:40:54
19	42f8fe02	\N	Деталь	S003.023	Заглушка м16х1.5	1	t	\N	t	\N	2026-06-02 15:14:59
20	24442dcc	\N	Деталь	L101.22.17.202	Втулка	1	t	\N	t	\N	2026-06-02 15:26:43
21	b45645f0	\N	Деталь	M001.103.000	Фланец вентилятора	1	t	\N	t	\N	2026-06-02 15:59:47
22	e6739046	\N	Деталь	S002.068.003	Переходник топливный	1	t	\N	t	\N	2026-09-02 08:27:52
23	268ba654	\N	Деталь	S002.060	Бонка  М12	1	t	\N	t	\N	2026-09-02 11:45:29
24	bc546d2c	\N	Деталь	S001.085.009	Штуцер с горловиной	1	t	\N	t	\N	2026-09-02 11:51:50
25	6ceda576	\N	Деталь	M001.03.010	Патрубок	1	t	\N	t	\N	2026-09-02 12:07:07
26	ed790c49	\N	Деталь	L101.22.04.001	Вал	1	t	\N	t	\N	2026-09-02 12:35:01
27	dc8ba083	\N	Деталь	M001.071.000.031	Фланец	1	t	\N	t	\N	2026-10-02 08:08:58
28	c4ed88a2	\N	Деталь	S003.024	Фланец переходной шкива к карданному валу	1	t	\N	t	\N	2026-10-02 09:20:30
29	400bc1fc	\N	Деталь	M103.38.30.007	Опора ДВС	1	t	\N	t	\N	2026-10-02 09:29:32
30	4cb34bac	\N	Деталь	M103.38.30.504	Опора	1	t	\N	t	\N	2026-10-02 09:48:03
31	466924c3	\N	Деталь	S003.009	Угольник ввертной	1	t	\N	t	\N	2026-10-02 10:12:34
32	c9e4a243	\N	Деталь	S001.085.007	Бонка  под сапун	1	t	\N	t	\N	2026-11-02 10:30:50
33	c4299a62	\N	Деталь	PO.TW.8.10.252.100.002	Корпус	1	t	\N	t	\N	2026-11-02 10:35:26
34	56cfa42b	\N	Деталь	S001.085.004	Муфта	1	t	\N	t	\N	2026-11-02 10:51:11
35	86264627	\N	Деталь	PO.TW.8.10.252.100.003	Упор подвижный	1	t	\N	t	\N	2026-11-02 11:06:03
36	26142bc2	\N	Деталь	PO.TW.8.10.252.100.001	Плита	1	t	\N	t	\N	2026-11-02 11:11:30
37	285ceb19	\N	Деталь	PO.TW.8.10.252.100.005	Направляющая	1	t	\N	t	\N	2026-11-02 12:56:10
38	a2e512d4	\N	Деталь	S001.073.004	Штуцер	1	t	\N	t	\N	2026-11-02 15:15:23
39	5936b38c	\N	Деталь	L101.38.10.014	Основание кронштейна	1	t	\N	t	\N	2026-12-02 08:13:30
40	7da634bc	\N	Деталь	PO.TW.8.10.252.100.004	Упор	1	t	\N	t	\N	2026-12-02 08:37:41
41	52a50b02	\N	Деталь	PO.TW.8.10.252.100.006	Винт	1	t	\N	t	\N	2026-12-02 10:18:44
42	2a273e8d	\N	Деталь	PO.TW.8.10.252.100.008	Болт установочный 10	1	t	\N	t	\N	2026-12-02 10:23:09
43	16b8cbce	\N	Деталь	MR20.02.00.282	Шайба шарнира	1	t	\N	t	\N	2026-02-13 08:19:04
44	44c9fc4a	\N	Деталь	MR20.02.00.292	Опора суппорта	1	t	\N	t	\N	2026-02-13 09:49:18
45	57effbc2	\N	Деталь	PO.TW.8.10.252.100.007	Бонка  10	1	t	\N	t	\N	2026-02-13 12:33:09
46	66d5abb5	\N	Деталь	MR20.02.00.222	Гайка приварная	1	t	\N	t	\N	2026-02-13 13:52:11
47	5346f1c7	\N	Деталь	MR20.02.00.291	Ступица передняя	1	t	\N	t	\N	2026-02-13 14:01:31
48	f4211d41	\N	Деталь	MR20.02.00.293	Корпус опоры	1	t	\N	t	\N	2026-02-13 14:10:57
49	3b386b1e	\N	Деталь	S002.128.002	Штуцер под шланг МБС 20	1	t	\N	t	\N	2026-02-13 14:18:53
50	19bf1f23	\N	Деталь	L101.20.03.104	Крепление	1	t	\N	t	\N	2026-02-13 14:26:48
51	b78442d2	\N	Деталь	L101.22.00.603	Втулка	1	t	\N	t	\N	2026-02-13 14:30:45
131	2be32c66-4812-44ce-a1e5-aa3518f0ebe9	\N	Деталь	PO.BMEX.404.200.009	Кольцо	1	t	\N	t	10	\N
132	180a1c8d-0aa4-4add-8a1b-bfefcda6f887	\N	Деталь	8.10.233	Кольцо стопорное	1	t	\N	t	10	\N
127	e34bbb19-246e-4acf-8b2c-e96c7dacf234	\N	detail	Test-001	тестовая	1	t	\N	t	2	\N
128	48b94545-e990-4723-b773-0978672590a4	\N	detail	Test-002	тестовая	1	t	\N	t	2	\N
129	028570f0-3d14-4e26-8060-a60e6294c8f1	\N	detail	Test-003	тестовая	1	t	\N	t	2	\N
\.


--
-- Data for Name: equipment; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.equipment (id, app_id, name, inventory_number, is_universal, operation_types, wage_with_taxes, multi_operational, power, cost, spi, tool_cost, tooling_cost, maintenance_cost, setup_cost, created_at, operator_id, is_active, default_working_hours, "position", has_workshop_inventory) FROM stdin;
1	8177cc8a	Вальцовочный ВМА-1550*6	\N	f	f874e0c8	112931	1	2	100000	10	\N	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	35	f
27	cf1274ac	Токарный ST16A25	\N	t	58ff46bf	120460	1	7.5	3655400	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	1	t
41	31c2eab7	Установка виброгалтовочная	\N	f	9f445169	15000	1	2.2	1500000	10	150	\N	50	\N	2026-02-20 21:07:36.079683	\N	f	7	44	f
10	8ea7c518	Установка СЭЛТ-ЗВУ-С-1000/200	\N	t	8b782868	120460	1	211	2000000	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	28	f
28	21f24f4a	Фрезерный DMU 50	\N	t	0da8f142	112931	1	30	13701042.41	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	7	t
31	30460445	Электроэрозионный SC40	\N	t	9bc3180b	120460	1	3	2604166.67	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	30	f
39	f1e5a1e9	Верстак	\N	f	0c75b6b8	90345	1	\N	\N	\N	\N	\N	\N	\N	2026-02-20 21:07:36.079683	\N	f	7	37	f
57	DIP300	Дип 300	\N	f	\N	\N	\N	10	\N	\N	\N	\N	\N	\N	2026-03-24 10:21:14.049285	\N	t	7	\N	f
4	a4202521	Зуборезный 525	\N	f	87a04d90	112931	1	6.2	583333.33	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	25	f
19	bc0c5b9d	Лазерный G-Weike LF3015GA	\N	f	8eb90a7e;c9b10df2	97874	1	35	12262584	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	32	f
21	a81d464e	Листогиб Durma AD-S30135	\N	f	7eeb7f47	112931	1	45	15521264.41	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	33	f
20	7d65be40	Листогиб ПЛГ-100.32	\N	f	7eeb7f47	112931	1	10.2	2025000	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	31	f
33	810b34da	Пескоструйный аппарат	\N	f	55e33d6e	90345	1	1.5	120000	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	f	7	38	f
34	b9e52720	Печь муфельная ПМ-5ПТР	\N	f	fc6438c7;8b782868;04f93ed5;0c41988b	\N	1	2.5	49900	5	\N	\N	15	15	2026-02-20 21:07:36.079683	\N	t	7	29	f
22	e6597f8a	Плазморез AlphaCut PS 2080 3M	\N	f	240923eb;c9b10df2	97874	1	3	1384310.83	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	34	f
42	\N	Сборочный стенд	\N	f	18	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-02-24 08:35:23.996908	\N	t	7	45	f
38	cb51bbe3	Слесарные работы	\N	f	16ac1e1c;c9b10df2;03c70c0f;e7cd9ecd;2c577dcf	90345	1	\N	\N	\N	50	\N	\N	\N	2026-02-20 21:07:36.079683	\N	t	7	42	f
53	16K20-1	Токарный 16К20_(1)	\N	f	58ff46bf;889e5e64;03c70c0f	112931	1	11.25	320000	3	106	15	15	15	2026-03-24 10:21:14.049285	\N	t	7	\N	f
54	16K20-2	Токарный 16К20_(2)	\N	f	58ff46bf;889e5e64;03c70c0f	112931	1	11.25	320000	3	106	15	15	15	2026-03-24 10:21:14.049285	\N	t	7	\N	f
24	4264ce86	Токарный CTX 510	\N	t	58ff46bf	120460	0	40	15187500	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	2	t
25	ca826b0a	Токарный KTL52M/500	\N	t	58ff46bf	120460	1	20	5920354.12	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	3	t
48	eq_Токарный_NL2500_N1	Токарный NL2500_№1	\N	f	58ff46bf	120460	1	40	13361553	10	212	15	30	30	2026-02-27 09:40:01.265198	\N	t	7	4	t
49	eq_Токарный_NL2500_N2	Токарный NL2500_№2	\N	f	58ff46bf	120460	1	40	13361553	10	212	15	30	30	2026-02-27 09:40:01.265198	\N	t	7	5	t
9	79d009e7	Сварочный полуавтомат	\N	f	6039a38a	112931	1	3	100000	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	f	7	37	f
12	57a6c744	Токарный 1К625Д	\N	f	58ff46bf	112931	1	11.87	410320.97	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	38	f
37	5d531026	Заточный станок CM-2	\N	f	0cc23083	105402	1	0.55	\N	\N	106	\N	15	\N	2026-02-20 21:07:36.079683	\N	t	7	41	f
35	05a23d37	Круглошлифовальный 3М151В	\N	f	a35cbae1;25	112931	1	10	350000	5	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	15	f
18	10761a30	Круглошлифовальный SOG-32100NC2	\N	f	a35cbae1;25	112931	1	8	7000000	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	16	f
40	e7da2285	Ленточно-пильный станок GEGZ4235	\N	f	c9b10df2	90345	1	2.2	450000	10	50	0	15	\N	2026-02-20 21:07:36.079683	\N	t	7	43	f
36	0243dde7	Ленточный гриндер Мастер 1250	\N	f	a35cbae1;16ac1e1c	105402	1	1.1	\N	\N	50	\N	15	\N	2026-02-20 21:07:36.079683	\N	t	7	11	f
7	9ea3cd1b	Пила JET HVBS712K-129E	\N	f	c9b10df2	90345	1	0.56	100000	10	50	\N	15	\N	2026-02-20 21:07:36.079683	\N	t	7	19	f
13	c4c8727e	Токарный 1М63МФ101	\N	f	58ff46bf;889e5e64	112931	1	13	410320.97	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	12	f
14	1175b7e0	Токарный ТС75	\N	f	58ff46bf	112931	1	11.87	83157.5	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	39	f
15	6ca12714	Трубогиб Stark GS70	\N	f	7eeb7f47	112931	1	4	1232138.33	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	40	f
16	ee289c67	Фрезерный 6Р81 горизонтальный	\N	f	0da8f142;889e5e64	105402	1	7.12	310000	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	20	f
17	efd681b6	Фрезерный 6С12 вертикальный	\N	f	0da8f142;889e5e64	105402	1	7.2	310000	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	21	f
32	8d0547c2	Шлифовальный 372Б	\N	f	a35cbae1;d92d3c69;37	112931	1	7.43	310000	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	18	f
2	195c0fd2	Зубодолбежный 5122	\N	f	06257b60	112931	1	5.17	614850.08	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	26	t
3	560b5d6c	Зубодолбежный ZSTWZ1000X10	\N	f	06257b60	112931	1	8.8	2780152.29	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	27	t
5	dd832a56	Зубофрезерный 53A20	\N	f	87a04d90	112931	1	8.95	1090149.92	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	23	t
6	11200b3d	Зубофрезерный 53A50	\N	f	87a04d90	112931	1	17.85	841666.67	3	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	24	t
8	9a7f26d2	Манипулятор резьбонарезной РМ16	\N	f	03c70c0f	90345	1	0.6	89808.75	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	36	t
23	0895ae4b	Сверлильный JET JMD-50-7	\N	f	2c577dcf	90345	1	1.5	318333.33	10	106	15	15	15	2026-02-20 21:07:36.079683	\N	t	7	35	t
55	16K20-3	Токарный 16К20_(3)	\N	f	58ff46bf;889e5e64;03c70c0f	112931	1	11.25	320000	3	106	15	15	15	2026-03-24 10:21:14.049285	\N	t	7	\N	f
56	16K20-4	Токарный 16К20_(4)	\N	f	58ff46bf;889e5e64;03c70c0f	112931	1	11.25	320000	3	106	15	15	15	2026-03-24 10:21:14.049285	\N	t	7	\N	f
50	eq_Токарный_NL2500_N3	Токарный NL2500_№3	\N	f	58ff46bf	120460	1	40	13361553	10	212	15	30	30	2026-02-27 09:40:01.265198	\N	t	7	6	t
51	eq_Фрезерный_IMU-5x400_N1	Фрезерный IMU-5x400_№1	\N	f	0da8f142	112931	1	50	19148287	10	212	15	30	30	2026-02-27 09:40:01.265198	\N	t	7	8	t
52	eq_Фрезерный_IMU-5x400_N2	Фрезерный IMU-5x400_№2	\N	f	0da8f142	112931	1	50	19148287	10	212	\N	30	30	2026-02-27 09:40:01.265198	\N	t	7	9	t
30	49c053d5	Фрезерный KVL1361	\N	t	0da8f142	150575	1	25	12793599.32	10	212	30	30	30	2026-02-20 21:07:36.079683	\N	t	7	10	t
\.


--
-- Data for Name: equipment_calendar; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.equipment_calendar (id, equipment_id, date, working_hours, is_working, notes, created_at, updated_at) FROM stdin;
2	39	2026-03-01 00:00:00	7	f	\N	\N	\N
1	39	2026-03-07 00:00:00	7	f	\N	\N	\N
6	39	2026-03-24 00:00:00	7	t	\N	\N	\N
5	39	2026-03-26 00:00:00	7	t	\N	\N	\N
7	39	2026-03-21 00:00:00	7	f	\N	\N	\N
4	39	2026-03-27 00:00:00	7	t	\N	\N	\N
3	39	2026-03-31 00:00:00	7	t	\N	\N	\N
14	51	2026-04-04 00:00:00	7	f	\N	\N	\N
18	25	2026-04-04 00:00:00	7	f	\N	\N	\N
20	27	2026-04-03 00:00:00	7	t	\N	\N	\N
22	24	2026-04-03 00:00:00	7	t	\N	\N	\N
23	25	2026-04-03 00:00:00	7	t	\N	\N	\N
24	48	2026-04-03 00:00:00	7	t	\N	\N	\N
25	49	2026-04-03 00:00:00	7	t	\N	\N	\N
26	50	2026-04-03 00:00:00	7	t	\N	\N	\N
27	28	2026-04-03 00:00:00	7	t	\N	\N	\N
28	51	2026-04-03 00:00:00	7	t	\N	\N	\N
29	52	2026-04-03 00:00:00	7	t	\N	\N	\N
30	30	2026-04-03 00:00:00	7	t	\N	\N	\N
31	36	2026-04-03 00:00:00	7	t	\N	\N	\N
32	13	2026-04-03 00:00:00	7	t	\N	\N	\N
33	35	2026-04-03 00:00:00	7	t	\N	\N	\N
34	18	2026-04-03 00:00:00	7	t	\N	\N	\N
35	32	2026-04-03 00:00:00	7	t	\N	\N	\N
36	7	2026-04-03 00:00:00	7	t	\N	\N	\N
37	16	2026-04-03 00:00:00	7	t	\N	\N	\N
38	17	2026-04-03 00:00:00	7	t	\N	\N	\N
39	5	2026-04-03 00:00:00	7	t	\N	\N	\N
40	6	2026-04-03 00:00:00	7	t	\N	\N	\N
41	4	2026-04-03 00:00:00	7	t	\N	\N	\N
42	2	2026-04-03 00:00:00	7	t	\N	\N	\N
43	3	2026-04-03 00:00:00	7	t	\N	\N	\N
44	10	2026-04-03 00:00:00	7	t	\N	\N	\N
45	34	2026-04-03 00:00:00	7	t	\N	\N	\N
46	31	2026-04-03 00:00:00	7	t	\N	\N	\N
47	20	2026-04-03 00:00:00	7	t	\N	\N	\N
48	19	2026-04-03 00:00:00	7	t	\N	\N	\N
49	21	2026-04-03 00:00:00	7	t	\N	\N	\N
50	22	2026-04-03 00:00:00	7	t	\N	\N	\N
51	1	2026-04-03 00:00:00	7	t	\N	\N	\N
52	23	2026-04-03 00:00:00	7	t	\N	\N	\N
53	8	2026-04-03 00:00:00	7	t	\N	\N	\N
54	39	2026-04-03 00:00:00	7	t	\N	\N	\N
55	9	2026-04-03 00:00:00	7	t	\N	\N	\N
56	33	2026-04-03 00:00:00	7	t	\N	\N	\N
57	12	2026-04-03 00:00:00	7	t	\N	\N	\N
58	14	2026-04-03 00:00:00	7	t	\N	\N	\N
59	15	2026-04-03 00:00:00	7	t	\N	\N	\N
60	37	2026-04-03 00:00:00	7	t	\N	\N	\N
61	38	2026-04-03 00:00:00	7	t	\N	\N	\N
62	40	2026-04-03 00:00:00	7	t	\N	\N	\N
63	41	2026-04-03 00:00:00	7	t	\N	\N	\N
64	42	2026-04-03 00:00:00	7	t	\N	\N	\N
65	53	2026-04-03 00:00:00	7	t	\N	\N	\N
66	54	2026-04-03 00:00:00	7	t	\N	\N	\N
67	55	2026-04-03 00:00:00	7	t	\N	\N	\N
68	56	2026-04-03 00:00:00	7	t	\N	\N	\N
69	57	2026-04-03 00:00:00	7	t	\N	\N	\N
\.


--
-- Data for Name: equipment_instances; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.equipment_instances (id, app_id, equipment_id, lotzman_id, number, operator_id, notes, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: geometry; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.geometry (id, app_id, name, primitive, prefix, unit, dimension1, dimension2, dimension3, for_volume, sketch, created_at) FROM stdin;
1	91910b8f	Круг	f	ø	пог.м	Диаметр, мм	\N	\N	f	\N	2026-02-20 21:07:36.069013
2	9094b4bc	Квадрат	f	□	пог.м	Сторона, мм	\N	\N	f	\N	2026-02-20 21:07:36.069013
3	c145677b	Лист	f	\N	м2	Толщина, мм	\N	\N	f	\N	2026-02-20 21:07:36.069013
4	abd1c863	Труба круглая	f	ø	пог.м	Диаметр, мм	Стенка, мм	\N	f	\N	2026-02-20 21:07:36.069013
5	d60d19ac	Труба квадратная	f	□	пог.м	Сторона, мм	Стенка, мм	\N	f	\N	2026-02-20 21:07:36.069013
6	dc131627	Труба прямоугольная	f	\N	пог.м	Сторона 1, мм	Сторона 2, мм	Стенка, мм	f	\N	2026-02-20 21:07:36.069013
7	b290ea0d	Шестигранник	f	\N	пог.м	Размер, мм	\N	\N	f	\N	2026-02-20 21:07:36.069013
8	21dbd1a6	Параллелепипед	t	\N	шт	L	W	S	f	/Конфигурация/Эскизы/Параллелепипед.png	2026-02-20 21:07:36.069013
9	e1a8d24e	Цилиндр	t	ø	шт	ø	L	\N	f	/Конфигурация/Эскизы/Цилиндр.png	2026-02-20 21:07:36.069013
10	c0ec2abd	Фасонная фигура	f	\N	шт	Длина, мм	Ширина, мм	Высота, мм	f	\N	2026-02-20 21:07:36.069013
11	71c76414	Раскрой	f	\N	шт	Толщина, мм	\N	\N	f	\N	2026-02-20 21:07:36.069013
12	b1b2cc1e	Цилиндр с отверстием	t	ø	шт	ø	d1	L	f	/Конфигурация/Эскизы/ЦилиндрОтверстие.png	2026-02-20 21:07:36.069013
13	6e89d053	По техпроцессу	t	\N	шт	\N	\N	\N	f	/Конфигурация/Эскизы/Техпроцесс.png	2026-02-20 21:07:36.069013
\.


--
-- Data for Name: inventory_changes; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.inventory_changes (id, item_id, old_quantity, new_quantity, changed_by, "timestamp") FROM stdin;
10	404	14	16	2	2026-04-02 14:39:55.404293
41	349	10	25	10	2026-04-08 01:44:35.962328
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.items (id, item_id, name, quantity, min_stock, category, location, created_at, updated_at, image_url, shop_url, specifications) FROM stdin;
401	19862	Зенковка 20,5 мм HSS DIN 335-C	10	1	Зенковка	\N	2026-02-19 02:27:03.027203	2026-03-03 08:12:00.275573	https://cncmagazine.ru/images/detailed/29/(16649_)_%D0%97%D0%B5%D0%BD%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0_20.5_%D0%BC%D0%BC_90_%D0%B3%D1%80%D0%B0%D0%B4%D1%83%D1%81%D0%BE%D0%B2,_HSS_Co5_DIN335-C,_%D1%86%D0%B8%D0%BB%D0%B8%D0%BD%D0%B4%D1%80%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%85%D0%B2%D0%BE%D1%81%D1%82%D0%BE%D0%B2%D0%B8%D0%BA_%D1%82_%D0%B0_%D0%B2_.jpg	https://cncmagazine.ru/zenkovki/zenkovka-20.5-mm-90-gradusov-hss-co5-din335-c/	\N
647	23299	Сверло CA55-3-0520	4	1	Сверло	\N	2026-02-19 02:27:03.114709	2026-04-20 09:13:26.607655	https://cncmagazine.ru/images/detailed/36/CA55-3_1_cxw7-bp.jpg	https://cncmagazine.ru/sverla-po-metallu/tverdosplavnye-sverla/ca55-3-0520-sverlo/	{"Диаметр": "5.2"}
440	11729	Метчик М18*2,0 ТА020182	3	1	Метчик	\N	2026-02-19 02:27:03.04745	2026-03-03 08:17:34.647225	https://cncmagazine.ru/images/detailed/45/05097_%D0%9C%D0%B5%D1%82%D1%87%D0%B8%D0%BA_%D0%9C18%D1%852_HSS-E_6H_%D1%81%D0%BF%D0%B8%D1%80%D0%B0%D0%BB%D1%8C%D0%BD%D0%B0%D1%8F_%D0%BA%D0%B0%D0%BD%D0%B0%D0%B2%D0%BA%D0%B0_38%C2%B0,_TiAlN_(TA020182)_%D1%82_%D0%B0_%D0%B2_%D1%81.jpg	https://cncmagazine.ru/metchiki/metchiki-metricheskaya-rezba/m18x2-metchik-hss-e-6h-spiralnaya-kanavka-38-tialn-ta020182/	\N
642	8288	Резьбофреза сборная SMT15-16H11U-1	2	1	\N	\N	2026-02-19 02:27:03.113386	2026-04-07 14:28:39.918477	\N	\N	\N
396	14439	Долбяк хвостовой М1,0 z=20 (Станок)	2	1	Долбяк	\N	2026-02-19 02:27:03.024459	2026-04-09 10:22:01.499487	https://www.rinscom.com/upload/iblock/cd1/dolbik-hvost.jpg	https://www.rinscom.com/katalog/metallorezhushchiy-instrument-prochiy/dolbyaki/74735/?srsltid=AfmBOoqj1HuXKBZbFQqRSCbEUIVJqcGeiIHHg86y-9ch6ahP9q5EXfNz	{"Тип": "Хвостовой"}
789	15124	Фреза 4-х зубая радиусная G8A47922 4*6*5*55*50	3	1	Фреза	\N	2026-02-19 02:27:03.165359	2026-04-20 08:32:44.115009	https://cncmagazine.ru/images/detailed/31/G8A47_nwaw-qj.jpg	https://cncmagazine.ru/frezy-po-metallu/celnye-tverdosplavnye/radiusnye-frezy-ru/g8a47922-freza-4-h-zubaya-radiusnaya-4-r1-x6x5-12-x55-x5070/	{"Диаметр": "4мм"}
650	14507	Сверло CA55-5-0350	9	1	\N	\N	2026-02-19 02:27:03.115559	2026-04-20 09:13:38.973028	\N	\N	\N
651	22824	Сверло CA55-5-0500	0	1	\N	\N	2026-02-19 02:27:03.11581	2026-04-20 09:13:50.056144	\N	\N	\N
643	15136	Ролик для накатки сетчатого рифления BL30°21,5-0,5-90°	1	1	\N	\N	2026-02-19 02:27:03.113647	2026-02-20 13:51:41.121227	\N	\N	\N
648	16232	Сверло CA55-3-1130	7	1	\N	\N	2026-02-19 02:27:03.114972	2026-02-20 13:51:41.121227	\N	\N	\N
649	10548	Сверло CA55-5-0300	6	1	\N	\N	2026-02-19 02:27:03.11529	2026-02-20 13:51:41.121227	\N	\N	\N
652	10708	Сверло CA55-5-0520	1	1	\N	\N	2026-02-19 02:27:03.116064	2026-02-20 13:51:41.121227	\N	\N	\N
653	13863	Сверло CA55-5-0600	5	1	\N	\N	2026-02-19 02:27:03.116319	2026-02-20 13:51:41.121227	\N	\N	\N
654	10832	Сверло CA55-5-0670	1	1	\N	\N	2026-02-19 02:27:03.116576	2026-02-20 13:51:41.121227	\N	\N	\N
655	10833	Сверло CA55-5-0680	8	1	\N	\N	2026-02-19 02:27:03.116843	2026-02-20 13:51:41.121227	\N	\N	\N
656	12301	Сверло CA55-5-0740	21	2	\N	\N	2026-02-19 02:27:03.117131	2026-02-20 13:51:41.121227	\N	\N	\N
657	10695	Сверло CAC55-5-0650	3	1	\N	\N	2026-02-19 02:27:03.117418	2026-02-20 13:51:41.121227	\N	\N	\N
658	10961	Сверло CAC55-5-0750	2	1	\N	\N	2026-02-19 02:27:03.11768	2026-02-20 13:51:41.121227	\N	\N	\N
659	22545	Сверло d 4,0 х 78х119 ц/х Р6М5К5 удлиненное с¶вышлиф.проф. ГОСТ 886-77	7	1	\N	\N	2026-02-19 02:27:03.117946	2026-02-20 13:51:41.121227	\N	\N	\N
660	15127	Сверло DA81-3-0800	2	1	\N	\N	2026-02-19 02:27:03.11821	2026-02-20 13:51:41.121227	\N	\N	\N
661	8751	Сверло DA81-3-1310	7	1	\N	\N	2026-02-19 02:27:03.118478	2026-02-20 13:51:41.121227	\N	\N	\N
662	15137	Сверло DA81-3-1500	5	1	\N	\N	2026-02-19 02:27:03.118781	2026-02-20 13:51:41.121227	\N	\N	\N
663	22745	Сверло DA81-5-0555	3	1	\N	\N	2026-02-19 02:27:03.119038	2026-02-20 13:51:41.121227	\N	\N	\N
664	23168	Сверло DA81-5-0610	1	1	\N	\N	2026-02-19 02:27:03.119294	2026-02-20 13:51:41.121227	\N	\N	\N
665	10690	Сверло DA81-5-0650	3	1	\N	\N	2026-02-19 02:27:03.119551	2026-02-20 13:51:41.121227	\N	\N	\N
666	15133	Сверло DA81-5-0680	3	1	\N	\N	2026-02-19 02:27:03.119808	2026-02-20 13:51:41.121227	\N	\N	\N
667	11036	Сверло DA81-5-0740	13	1	\N	\N	2026-02-19 02:27:03.120074	2026-02-20 13:51:41.121227	\N	\N	\N
668	10692	Сверло DA81-5-0870	4	1	\N	\N	2026-02-19 02:27:03.120341	2026-02-20 13:51:41.121227	\N	\N	\N
669	10964	Сверло DA81-5-0880	9	1	\N	\N	2026-02-19 02:27:03.120597	2026-02-20 13:51:41.121227	\N	\N	\N
670	22419	Сверло DA81-5-0930	14	1	\N	\N	2026-02-19 02:27:03.120853	2026-02-20 13:51:41.121227	\N	\N	\N
419	10585	Сверло DA81-5-1025	17	1	\N	\N	2026-02-19 02:27:03.038664	2026-02-20 13:51:41.121227	\N	\N	\N
671	22129	Сверло DA81-5-1120	3	1	\N	\N	2026-02-19 02:27:03.132334	2026-02-20 13:51:41.121227	\N	\N	\N
672	19860	Сверло DA81-5-1150	3	1	\N	\N	2026-02-19 02:27:03.132897	2026-02-20 13:51:41.121227	\N	\N	\N
673	13318	Сверло DA81-5-1250	5	1	\N	\N	2026-02-19 02:27:03.133205	2026-02-20 13:51:41.121227	\N	\N	\N
674	12509	Сверло DA81-5-1400	3	1	\N	\N	2026-02-19 02:27:03.133474	2026-02-20 13:51:41.121227	\N	\N	\N
675	11309	Сверло DA81-5C-0420	6	1	\N	\N	2026-02-19 02:27:03.133753	2026-02-20 13:51:41.121227	\N	\N	\N
676	9592	Сверло DA81-5C-0500	3	1	\N	\N	2026-02-19 02:27:03.134016	2026-02-20 13:51:41.121227	\N	\N	\N
677	10584	Сверло DA81-5C-1030	9	1	\N	\N	2026-02-19 02:27:03.134273	2026-02-20 13:51:41.121227	\N	\N	\N
678	11307	Сверло DA83-3-0900	8	1	\N	\N	2026-02-19 02:27:03.134529	2026-02-20 13:51:41.121227	\N	\N	\N
679	10689	Сверло DA83-5С-0650	2	1	\N	\N	2026-02-19 02:27:03.134786	2026-02-20 13:51:41.121227	\N	\N	\N
680	10703	Сверло DA83-5С-0850	1	1	\N	\N	2026-02-19 02:27:03.135043	2026-02-20 13:51:41.121227	\N	\N	\N
681	10702	Сверло DA83-5С-1100	6	1	\N	\N	2026-02-19 02:27:03.135342	2026-02-20 13:51:41.121227	\N	\N	\N
683	15135	Сверло DH500140 14*14*77*125	1	1	\N	\N	2026-02-19 02:27:03.135877	2026-02-20 13:51:41.121227	\N	\N	\N
684	11306	Сверло DH89-3-0900	3	1	\N	\N	2026-02-19 02:27:03.136129	2026-02-20 13:51:41.121227	\N	\N	\N
685	15129	Сверло DH89-3-1000	3	1	\N	\N	2026-02-19 02:27:03.136391	2026-02-20 13:51:41.121227	\N	\N	\N
686	11038	Сверло DM861-5С-0550	4	1	\N	\N	2026-02-19 02:27:03.136661	2026-02-20 13:51:41.121227	\N	\N	\N
687	10962	Сверло DM861-5С-0850	7	1	\N	\N	2026-02-19 02:27:03.136932	2026-02-20 13:51:41.121227	\N	\N	\N
929	00000	Сверло корпус UD30.SP07.240.W25	2	1	Сверло	\N	2026-04-23 04:44:17.524622	2026-04-23 12:45:02.369251	https://cncmagazine.ru/images/detailed/6/UD__j8nd-sa.jpg	https://cncmagazine.ru/sverla-po-metallu/korpusnye-sverla/korpusnoe-sverlo-ud30.sp07.240.w25/	\N
378	8755	Державка токарная MGIVL3732-5	1	1	\N	\N	2026-02-19 02:27:03.014519	2026-02-20 13:51:41.121227	\N	\N	\N
379	8726	Державка токарная MTHR2525M43	5	1	\N	\N	2026-02-19 02:27:03.014917	2026-02-20 13:51:41.121227	\N	\N	\N
380	9922	Державка токарная MVUNL2525M16	2	1	\N	\N	2026-02-19 02:27:03.015475	2026-02-20 13:51:41.121227	\N	\N	\N
381	10706	Державка токарная S25R-MVQNR1504	2	1	\N	\N	2026-02-19 02:27:03.016197	2026-02-20 13:51:41.121227	\N	\N	\N
382	10705	Державка токарная S25R-MVQNR16	4	1	\N	\N	2026-02-19 02:27:03.017127	2026-02-20 13:51:41.121227	\N	\N	\N
383	11567	Державка токарная S25R-SDQCR11	4	1	\N	\N	2026-02-19 02:27:03.017785	2026-02-20 13:51:41.121227	\N	\N	\N
384	11745	Державка токарная S32S	2	1	\N	\N	2026-02-19 02:27:03.018382	2026-02-20 13:51:41.121227	\N	\N	\N
385	12527	Державка токарная SNR0025R22	1	1	\N	\N	2026-02-19 02:27:03.018858	2026-02-20 13:51:41.121227	\N	\N	\N
386	12528	Державка токарная SVER2525M22	2	1	\N	\N	2026-02-19 02:27:03.019322	2026-02-20 13:51:41.121227	\N	\N	\N
387	9594	Державка токарная SVNR0032S16	2	1	\N	\N	2026-02-19 02:27:03.019803	2026-02-20 13:51:41.121227	\N	\N	\N
388	13860	Державка токарная SWR2525M16H	5	1	\N	\N	2026-02-19 02:27:03.020353	2026-02-20 13:51:41.121227	\N	\N	\N
389	9921	Державка токарная TVHNL2525M16	2	1	\N	\N	2026-02-19 02:27:03.020848	2026-02-20 13:51:41.121227	\N	\N	\N
390	9793	Держатель инструмента В2-40*25*44	2	1	\N	\N	2026-02-19 02:27:03.021287	2026-02-20 13:51:41.121227	\N	\N	\N
392	12092	Держатель инструмента Е2-40*16	1	1	\N	\N	2026-02-19 02:27:03.022274	2026-02-20 13:51:41.121227	\N	\N	\N
393	8725	Держатель инструмента Е2-40*25	4	1	\N	\N	2026-02-19 02:27:03.022729	2026-02-20 13:51:41.121227	\N	\N	\N
394	9596	Держатель инструмента Е2-40*32	2	1	\N	\N	2026-02-19 02:27:03.023209	2026-02-20 13:51:41.121227	\N	\N	\N
395	10520	Держатель инструмента Е4-40*32	5	1	\N	\N	2026-02-19 02:27:03.023868	2026-02-20 13:51:41.121227	\N	\N	\N
397	17776	Долбяк хвостовой М1,0 z=26(Станок)	5	1	\N	\N	2026-02-19 02:27:03.02506	2026-02-20 13:51:41.121227	\N	\N	\N
398	8985	Долбяк хвостовой М1,5 z=25 ( Станок)	5	1	\N	\N	2026-02-19 02:27:03.025548	2026-02-20 13:51:41.121227	\N	\N	\N
399	15539	Долбяк чашечный М3,5 z=22 (станок)	4	1	\N	\N	2026-02-19 02:27:03.026076	2026-02-20 13:51:41.121227	\N	\N	\N
400	15540	Долбяк чашечный М3,5 z=28 (станок)	4	1	\N	\N	2026-02-19 02:27:03.026609	2026-02-20 13:51:41.121227	\N	\N	\N
402	22531	Зенковка коническая цх 20.0х24х 60х 90гр. хв.10мм¶Р6М5 тип 6 Z=6 2353-0112	10	1	\N	\N	2026-02-19 02:27:03.027852	2026-02-20 13:51:41.121227	\N	\N	\N
403	22532	Зенковка коническая цх 25.0х29х 65х 90гр. хв.10мм¶Р6М5 тип 6 Z=6 2353-0113	4	1	\N	\N	2026-02-19 02:27:03.028437	2026-02-20 13:51:41.121227	\N	\N	\N
405	11374	Корпус антивибрационный державки V25H-255-7D	1	1	\N	\N	2026-02-19 02:27:03.029479	2026-02-20 13:51:41.121227	\N	\N	\N
406	9999	Корпус сверла N080/89-12WN-3D-CA	2	1	\N	\N	2026-02-19 02:27:03.030039	2026-02-20 13:51:41.121227	\N	\N	\N
407	10000	Корпус сверла N140/149-16WN-3D-CA	2	1	\N	\N	2026-02-19 02:27:03.03051	2026-02-20 13:51:41.121227	\N	\N	\N
408	11376	Корпус сверла N180/189-25WN-5D-CA	1	1	\N	\N	2026-02-19 02:27:03.030909	2026-02-20 13:51:41.121227	\N	\N	\N
409	9568	Корпус фрезы S666VV-019-16 SAU	3	1	\N	\N	2026-02-19 02:27:03.033068	2026-02-20 13:51:41.121227	\N	\N	\N
410	23532	Круг шлифовальный 100*63*20 F46	48	4	\N	\N	2026-02-19 02:27:03.034346	2026-02-20 13:51:41.121227	\N	\N	\N
411	23531	Круг шлифовальный 100*63*20 F60	24	2	\N	\N	2026-02-19 02:27:03.035158	2026-02-20 13:51:41.121227	\N	\N	\N
412	23544	Круг шлифовальный 125*10*32 F46	35	3	\N	\N	2026-02-19 02:27:03.035602	2026-02-20 13:51:41.121227	\N	\N	\N
413	23545	Круг шлифовальный 125*6*32 F46	45	4	\N	\N	2026-02-19 02:27:03.036016	2026-02-20 13:51:41.121227	\N	\N	\N
414	18931	Круг шлифовальный 150*25*32 25А F80	4	1	\N	\N	2026-02-19 02:27:03.036435	2026-02-20 13:51:41.121227	\N	\N	\N
415	20241	Круг шлифовальный 175*20*32 25А 40СМ	1	1	\N	\N	2026-02-19 02:27:03.036877	2026-02-20 13:51:41.121227	\N	\N	\N
416	11964	Круг шлифовальный 175*20*32 64С 40СМ	1	1	\N	\N	2026-02-19 02:27:03.037296	2026-02-20 13:51:41.121227	\N	\N	\N
417	9301	Круг шлифовальный 20*25*6 F60	200	20	\N	\N	2026-02-19 02:27:03.037722	2026-02-20 13:51:41.121227	\N	\N	\N
418	10586	Круг шлифовальный 200*20*32 25А 40СМ	1	1	\N	\N	2026-02-19 02:27:03.038162	2026-02-20 13:51:41.121227	\N	\N	\N
420	21044	Круг шлифовальный 250*25*32 25А 25СМ АГ	1	1	\N	\N	2026-02-19 02:27:03.039175	2026-02-20 13:51:41.121227	\N	\N	\N
421	18011	Круг шлифовальный 350*40*127 25А 40СМ	1	1	\N	\N	2026-02-19 02:27:03.039662	2026-02-20 13:51:41.121227	\N	\N	\N
422	8296	Лезвие отрезное SPB526-S	3	1	\N	\N	2026-02-19 02:27:03.040076	2026-02-20 13:51:41.121227	\N	\N	\N
423	12315	Метчик G1/4	25	2	\N	\N	2026-02-19 02:27:03.040497	2026-02-20 13:51:41.121227	\N	\N	\N
424	12340	Метчик G1/8	20	2	\N	\N	2026-02-19 02:27:03.040928	2026-02-20 13:51:41.121227	\N	\N	\N
425	9284	Метчик HSS-E M5*0.8 6H	5	1	\N	\N	2026-02-19 02:27:03.041306	2026-02-20 13:51:41.121227	\N	\N	\N
426	10735	Метчик гаечный М6*1,0	7	1	\N	\N	2026-02-19 02:27:03.041686	2026-02-20 13:51:41.121227	\N	\N	\N
427	8771	Метчик М10*1 для глухих отверстий,с покрытием TiCN-C	7	1	\N	\N	2026-02-19 02:27:03.042094	2026-02-20 13:51:41.121227	\N	\N	\N
428	13882	Метчик М10*1,25 для глухих отверстий,с покрытием TiCN-C	8	1	\N	\N	2026-02-19 02:27:03.04253	2026-02-20 13:51:41.121227	\N	\N	\N
429	15366	Метчик М10*1,5 для глухих отверстий,с покрытием TiCN-C	26	2	\N	\N	2026-02-19 02:27:03.042986	2026-02-20 13:51:41.121227	\N	\N	\N
430	15985	Метчик М11*1,25 для глухих отверстий	2	1	\N	\N	2026-02-19 02:27:03.043442	2026-02-20 13:51:41.121227	\N	\N	\N
431	13278	Метчик М11*1,5	20	2	\N	\N	2026-02-19 02:27:03.04387	2026-02-20 13:51:41.121227	\N	\N	\N
432	3293	Метчик М12*1,5	6	1	\N	\N	2026-02-19 02:27:03.044325	2026-02-20 13:51:41.121227	\N	\N	\N
433	19863	Метчик М12*1,5 для глухих отверстий,с покрытием TiCN-C	22	2	\N	\N	2026-02-19 02:27:03.044717	2026-02-20 13:51:41.121227	\N	\N	\N
434	8772	Метчик М12*1,75 для глухих отверстий,с покрытием TiCN-C	21	2	\N	\N	2026-02-19 02:27:03.045129	2026-02-20 13:51:41.121227	\N	\N	\N
435	13884	Метчик М14*1,5 для глухих отверстий,с покрытием TiCN-C	3	1	\N	\N	2026-02-19 02:27:03.045517	2026-02-20 13:51:41.121227	\N	\N	\N
436	8773	Метчик М14*2 для глухих отверстий,с покрытием TiCN-C	20	2	\N	\N	2026-02-19 02:27:03.045908	2026-02-20 13:51:41.121227	\N	\N	\N
437	13883	Метчик М16*1,5 для глухих отверстий,с покрытием TiCN-C	4	1	\N	\N	2026-02-19 02:27:03.046274	2026-02-20 13:51:41.121227	\N	\N	\N
438	3301	Метчик М16*2,0	6	1	\N	\N	2026-02-19 02:27:03.046638	2026-02-20 13:51:41.121227	\N	\N	\N
439	13885	Метчик М18*1,5 для глухих отверстий,с покрытием TiCN-C	26	2	\N	\N	2026-02-19 02:27:03.047027	2026-02-20 13:51:41.121227	\N	\N	\N
441	13886	Метчик М20*1,5 для глухих отверстий,с покрытием TiCN-C	10	1	\N	\N	2026-02-19 02:27:03.04791	2026-02-20 13:51:41.121227	\N	\N	\N
442	13887	Метчик М22*1,5 для глухих отверстий,с покрытием TiCN-C	10	1	\N	\N	2026-02-19 02:27:03.048445	2026-02-20 13:51:41.121227	\N	\N	\N
404	11283	Карандаш алмазный	16	1	Карандаш	\N	2026-02-19 02:27:03.028897	2026-04-09 10:02:09.630211	\N	\N	\N
443	8769	Метчик М4*0,7 для глухих отверстий	5	1	\N	\N	2026-02-19 02:27:03.049122	2026-02-20 13:51:41.121227	\N	\N	\N
444	8770	Метчик М6*1 для глухих отверстий,с покрытием TiCN-C	19	1	\N	\N	2026-02-19 02:27:03.049672	2026-02-20 13:51:41.121227	\N	\N	\N
445	16277	Метчик М8*1,0 для глухих отверстий,с покрытием TiCN-C	16	1	\N	\N	2026-02-19 02:27:03.050153	2026-02-20 13:51:41.121227	\N	\N	\N
446	3276	Метчик М8*1,25	10	1	\N	\N	2026-02-19 02:27:03.050586	2026-02-20 13:51:41.121227	\N	\N	\N
447	15365	Метчик М8*1,25 для глухих отверстий,с покрытием TiCN-C	29	2	\N	\N	2026-02-19 02:27:03.051011	2026-02-20 13:51:41.121227	\N	\N	\N
448	21157	Метчик М9*1	14	1	\N	\N	2026-02-19 02:27:03.051609	2026-02-20 13:51:41.121227	\N	\N	\N
449	14147	Метчик раскатник HSS M10*1 6H	13	1	\N	\N	2026-02-19 02:27:03.052225	2026-02-20 13:51:41.121227	\N	\N	\N
450	16961	Метчик раскатник HSS M10*1,25 6H	15	1	\N	\N	2026-02-19 02:27:03.052818	2026-02-20 13:51:41.121227	\N	\N	\N
451	11034	Метчик раскатник HSS M10*1,5 6H	26	2	\N	\N	2026-02-19 02:27:03.053393	2026-02-20 13:51:41.121227	\N	\N	\N
645	23300	Сверло CA55-3-0320	9	1	\N	\N	2026-02-19 02:27:03.114194	2026-02-20 13:51:41.121227	\N	\N	\N
452	15967	Метчик раскатник HSS M12*1,25 6H	1	1	\N	\N	2026-02-19 02:27:03.053959	2026-02-20 13:51:41.121227	\N	\N	\N
453	16225	Метчик раскатник HSS M14*2,0 6H	10	1	\N	\N	2026-02-19 02:27:03.054691	2026-02-20 13:51:41.121227	\N	\N	\N
454	11035	Метчик раскатник HSS M8*1,25 6H	34	3	\N	\N	2026-02-19 02:27:03.055273	2026-02-20 13:51:41.121227	\N	\N	\N
455	20310	Метчик раскатник HSS М5*0,8 6H	15	1	\N	\N	2026-02-19 02:27:03.055647	2026-02-20 13:51:41.121227	\N	\N	\N
456	11050	Метчик раскатник M12*1,75 	11	1	\N	\N	2026-02-19 02:27:03.056054	2026-02-20 13:51:41.121227	\N	\N	\N
457	9144	Микросверло по металлу 1,2мм CHD1200	2	1	\N	\N	2026-02-19 02:27:03.056481	2026-02-20 13:51:41.121227	\N	\N	\N
458	4707	Минирезец IMM-BR40R10L10 	3	1	\N	\N	2026-02-19 02:27:03.056918	2026-02-20 13:51:41.121227	\N	\N	\N
459	12610	Минирезец PSTIR60200-55°-KTX	2	1	\N	\N	2026-02-19 02:27:03.057332	2026-02-20 13:51:41.121227	\N	\N	\N
460	12612	Минирезец PSTIR60200-60°-KTX	2	1	\N	\N	2026-02-19 02:27:03.057743	2026-02-20 13:51:41.121227	\N	\N	\N
461	12609	Минирезец PSTIR80220-55°-KTX	5	1	\N	\N	2026-02-19 02:27:03.058153	2026-02-20 13:51:41.121227	\N	\N	\N
462	12611	Минирезец PSTIR80220-60°-KTX	6	1	\N	\N	2026-02-19 02:27:03.058559	2026-02-20 13:51:41.121227	\N	\N	\N
463	19789	Минирезец SBFR50200R020-D6	10	1	\N	\N	2026-02-19 02:27:03.05897	2026-02-20 13:51:41.121227	\N	\N	\N
464	19790	Минирезец SBFR60200R020-D6	9	1	\N	\N	2026-02-19 02:27:03.059347	2026-02-20 13:51:41.121227	\N	\N	\N
465	12632	Минирезец SBPR80300R015-D8	2	1	\N	\N	2026-02-19 02:27:03.059753	2026-02-20 13:51:41.121227	\N	\N	\N
466	12631	Минирезец SBUR80300R020-D8	7	1	\N	\N	2026-02-19 02:27:03.060263	2026-02-20 13:51:41.121227	\N	\N	\N
467	9623	Минирезец SBWR15160R015-D8	2	1	\N	\N	2026-02-19 02:27:03.060702	2026-02-20 13:51:41.121227	\N	\N	\N
468	22631	Наконечник для полировки R1.0	3	1	\N	\N	2026-02-19 02:27:03.061158	2026-02-20 13:51:41.121227	\N	\N	\N
469	22632	Наконечник для полировки R2.0	4	1	\N	\N	2026-02-19 02:27:03.061601	2026-02-20 13:51:41.121227	\N	\N	\N
470	8292	Оправка для фрез ВТ40-FMB22-60	1	1	\N	\N	2026-02-19 02:27:03.062027	2026-02-20 13:51:41.121227	\N	\N	\N
471	12963	Патрон HSK63A-MTB2-120	2	1	\N	\N	2026-02-19 02:27:03.062421	2026-02-20 13:51:41.121227	\N	\N	\N
472	12965	Патрон HSK63A-MTB4-160	4	1	\N	\N	2026-02-19 02:27:03.062788	2026-02-20 13:51:41.121227	\N	\N	\N
473	13501	Патрон быстросъемный резьбонарезной BT40-GT12-110L	1	1	\N	\N	2026-02-19 02:27:03.06315	2026-02-20 13:51:41.121227	\N	\N	\N
474	8960	Патрон гидропластовый HSK63A-PHC08-80	2	1	\N	\N	2026-02-19 02:27:03.063536	2026-02-20 13:51:41.121227	\N	\N	\N
475	12639	Патрон термоусадочный HSK63A-SF06-120	1	1	\N	\N	2026-02-19 02:27:03.06395	2026-02-20 13:51:41.121227	\N	\N	\N
476	12640	Патрон термоусадочный HSK63A-SF08-120	2	1	\N	\N	2026-02-19 02:27:03.064391	2026-02-20 13:51:41.121227	\N	\N	\N
477	14858	Патрон термоусадочный HSK63A-SF10-120	2	1	\N	\N	2026-02-19 02:27:03.064798	2026-02-20 13:51:41.121227	\N	\N	\N
478	20785	Патрон термоусадочный HSK63A-SF12-120	1	1	\N	\N	2026-02-19 02:27:03.065201	2026-02-20 13:51:41.121227	\N	\N	\N
479	11024	Патрон термоусадочный ВТ40-SF04-80	1	1	\N	\N	2026-02-19 02:27:03.065587	2026-02-20 13:51:41.121227	\N	\N	\N
480	17043	Патрон термоусадочный ВТ40-SF08-90	1	1	\N	\N	2026-02-19 02:27:03.066128	2026-02-20 13:51:41.121227	\N	\N	\N
481	15139	Патрон термоусадочный ВТ40-SF12-90	2	1	\N	\N	2026-02-19 02:27:03.066725	2026-02-20 13:51:41.121227	\N	\N	\N
482	12634	Патрон торцевой HSK63A-FMB22-100	1	1	\N	\N	2026-02-19 02:27:03.067424	2026-02-20 13:51:41.121227	\N	\N	\N
483	12633	Патрон торцевой HSK63A-FMB40-100	2	1	\N	\N	2026-02-19 02:27:03.068052	2026-02-20 13:51:41.121227	\N	\N	\N
484	14571	Патрон фрезерный HSK63A-SLN25-110	1	1	\N	\N	2026-02-19 02:27:03.068451	2026-02-20 13:51:41.121227	\N	\N	\N
485	17542	Патрон цанговый BT40-ER32-100	2	1	\N	\N	2026-02-19 02:27:03.068812	2026-02-20 13:51:41.121227	\N	\N	\N
486	10121	Патрон цанговый BT40-SC25-105	2	1	\N	\N	2026-02-19 02:27:03.06922	2026-02-20 13:51:41.121227	\N	\N	\N
487	12607	Патрон цанговый HSK63A-ER32-160	2	1	\N	\N	2026-02-19 02:27:03.069599	2026-02-20 13:51:41.121227	\N	\N	\N
488	8469	Патрон цанговый HSK63A-ER32-75	3	1	\N	\N	2026-02-19 02:27:03.069978	2026-02-20 13:51:41.121227	\N	\N	\N
489	22286	Патрон цанговый MTB2-ER16-40L (с конусом Морзе)	1	1	\N	\N	2026-02-19 02:27:03.070349	2026-02-20 13:51:41.121227	\N	\N	\N
490	22285	Патрон цанговый MTB3-ER16-40L (с конусом Морзе)	1	1	\N	\N	2026-02-19 02:27:03.070734	2026-02-20 13:51:41.121227	\N	\N	\N
491	16964	Патрон цанговый SL20-ER32-80L	6	1	\N	\N	2026-02-19 02:27:03.071109	2026-02-20 13:51:41.121227	\N	\N	\N
492	10546	Патрон цанговый SL25-ER32-80L	8	1	\N	\N	2026-02-19 02:27:03.071487	2026-02-20 13:51:41.121227	\N	\N	\N
493	16689	Пластина FS177-Z309D-400 DM215	2	1	\N	\N	2026-02-19 02:27:03.071866	2026-02-20 13:51:41.121227	\N	\N	\N
494	12529	Пластина твердосплавная 22VER5.0TR PM30	6	1	\N	\N	2026-02-19 02:27:03.072233	2026-02-20 13:51:41.121227	\N	\N	\N
495	11299	Пластина твердосплавная DNMG150604-QF IA80F	49	4	\N	\N	2026-02-19 02:27:03.072641	2026-02-20 13:51:41.121227	\N	\N	\N
496	11295	Пластина твердосплавная GEL300DM15-E PM125	18	1	\N	\N	2026-02-19 02:27:03.073001	2026-02-20 13:51:41.121227	\N	\N	\N
497	12081	Пластина твердосплавная MRMN400-M PM310	10	1	\N	\N	2026-02-19 02:27:03.073344	2026-02-20 13:51:41.121227	\N	\N	\N
498	11305	Пластина твердосплавная QCMB030003N-MT CA5020	17	1	\N	\N	2026-02-19 02:27:03.073685	2026-02-20 13:51:41.121227	\N	\N	\N
499	12966	Пластина твердосплавная SNEU1206ANEN-GM IA6330	16	1	\N	\N	2026-02-19 02:27:03.074021	2026-02-20 13:51:41.121227	\N	\N	\N
500	22555	Пластина твердосплавная TDC3-LH PM310	20	2	\N	\N	2026-02-19 02:27:03.074367	2026-02-20 13:51:41.121227	\N	\N	\N
501	12300	Пластина твердосплавная WCMX080412-FN CA5220	16	1	\N	\N	2026-02-19 02:27:03.074707	2026-02-20 13:51:41.121227	\N	\N	\N
502	21129	Пластина твердосплавная WCMX080412-XM MK330	10	1	\N	\N	2026-02-19 02:27:03.075045	2026-02-20 13:51:41.121227	\N	\N	\N
503	22090	Пластина твердосплавная WNMG060404-UF YG3030	5	1	\N	\N	2026-02-19 02:27:03.075378	2026-02-20 13:51:41.121227	\N	\N	\N
504	11297	Пластина твердосплавная WNMG080412-MD BP6225	66	6	\N	\N	2026-02-19 02:27:03.075739	2026-02-20 13:51:41.121227	\N	\N	\N
505	11391	Пластина токарная  CNMG 090308-MF	7	1	\N	\N	2026-02-19 02:27:03.076113	2026-02-20 13:51:41.121227	\N	\N	\N
506	10006	Пластина токарная  CNMG 120412-PPMK6020	10	1	\N	\N	2026-02-19 02:27:03.076573	2026-02-20 13:51:41.121227	\N	\N	\N
644	6657	Сверло 10*121*184	6	1	\N	\N	2026-02-19 02:27:03.113924	2026-02-20 13:51:41.121227	\N	\N	\N
507	10686	Пластина токарная  MGMN400-CBN	7	1	\N	\N	2026-02-19 02:27:03.077011	2026-02-20 13:51:41.121227	\N	\N	\N
508	12090	Пластина токарная  MGMN400-G BPG20B	6	1	\N	\N	2026-02-19 02:27:03.077395	2026-02-20 13:51:41.121227	\N	\N	\N
509	12891	Пластина токарная  MGMN4004-МТ IA6330	9	1	\N	\N	2026-02-19 02:27:03.077757	2026-02-20 13:51:41.121227	\N	\N	\N
510	11814	Пластина токарная  MGMN500-М	28	2	\N	\N	2026-02-19 02:27:03.078079	2026-02-20 13:51:41.121227	\N	\N	\N
511	8756	Пластина токарная  MGMN500-М BPG20B	121	12	\N	\N	2026-02-19 02:27:03.078343	2026-02-20 13:51:41.121227	\N	\N	\N
512	20571	Пластина токарная  MGMN5004-МТ IA6330	5	1	\N	\N	2026-02-19 02:27:03.078621	2026-02-20 13:51:41.121227	\N	\N	\N
513	8959	Пластина токарная  MGMN5008-МТ IA6330	1	1	\N	\N	2026-02-19 02:27:03.078867	2026-02-20 13:51:41.121227	\N	\N	\N
514	16953	Пластина токарная  MGMN600-M OP1215	18	1	\N	\N	2026-02-19 02:27:03.079117	2026-02-20 13:51:41.121227	\N	\N	\N
515	16954	Пластина токарная  MGMN600-M OP1315	9	1	\N	\N	2026-02-19 02:27:03.079377	2026-02-20 13:51:41.121227	\N	\N	\N
646	22825	Сверло CA55-3-0500	4	1	\N	\N	2026-02-19 02:27:03.114451	2026-02-20 13:51:41.121227	\N	\N	\N
516	9627	Пластина токарная  NP VNGA 160404 GA4 BC8120	5	1	\N	\N	2026-02-19 02:27:03.079649	2026-02-20 13:51:41.121227	\N	\N	\N
517	11569	Пластина токарная  RT 1601G	10	1	\N	\N	2026-02-19 02:27:03.079949	2026-02-20 13:51:41.121227	\N	\N	\N
518	9602	Пластина токарная  WCMX030208-FN CA5220	26	2	\N	\N	2026-02-19 02:27:03.080242	2026-02-20 13:51:41.121227	\N	\N	\N
519	15428	Пластина токарная  WCMX080412-FN CA5020	16	1	\N	\N	2026-02-19 02:27:03.080522	2026-02-20 13:51:41.121227	\N	\N	\N
520	13574	Пластина токарная  WNGU 040304-GM IA6330	20	2	\N	\N	2026-02-19 02:27:03.080796	2026-02-20 13:51:41.121227	\N	\N	\N
521	14488	Пластина токарная  WNMG 060404-LM IM7325	4	1	\N	\N	2026-02-19 02:27:03.081071	2026-02-20 13:51:41.121227	\N	\N	\N
522	8329	Пластина токарная 11IR125ISO-HR52013	10	1	\N	\N	2026-02-19 02:27:03.081321	2026-02-20 13:51:41.121227	\N	\N	\N
523	11737	Пластина токарная 11IR14W-TC IM7325	5	1	\N	\N	2026-02-19 02:27:03.081554	2026-02-20 13:51:41.121227	\N	\N	\N
524	9134	Пластина токарная 11IR150ISO-HR52013	10	1	\N	\N	2026-02-19 02:27:03.081844	2026-02-20 13:51:41.121227	\N	\N	\N
525	16960	Пластина токарная 11IRA55-TC IM7325	50	5	\N	\N	2026-02-19 02:27:03.082088	2026-02-20 13:51:41.121227	\N	\N	\N
526	16959	Пластина токарная 11IRA60-TC IM7325	27	2	\N	\N	2026-02-19 02:27:03.082373	2026-02-20 13:51:41.121227	\N	\N	\N
527	10298	Пластина токарная 11NR1.50iSO-KVX	10	1	\N	\N	2026-02-19 02:27:03.082617	2026-02-20 13:51:41.121227	\N	\N	\N
528	8709	Пластина токарная 11NR1.75iSO-KVX	9	1	\N	\N	2026-02-19 02:27:03.082857	2026-02-20 13:51:41.121227	\N	\N	\N
529	10299	Пластина токарная 11NR2.00iSO-KVX	20	2	\N	\N	2026-02-19 02:27:03.083106	2026-02-20 13:51:41.121227	\N	\N	\N
530	8289	Пластина токарная 11UIDA60 DM215	16	1	\N	\N	2026-02-19 02:27:03.083355	2026-02-20 13:51:41.121227	\N	\N	\N
531	11741	Пластина токарная 16ER1.75ISO-TC IM7325	30	3	\N	\N	2026-02-19 02:27:03.083616	2026-02-20 13:51:41.121227	\N	\N	\N
532	11736	Пластина токарная 16ER11W-TC IM7325	9	1	\N	\N	2026-02-19 02:27:03.083993	2026-02-20 13:51:41.121227	\N	\N	\N
533	9595	Пластина токарная 16VNRAG60 DM215	20	2	\N	\N	2026-02-19 02:27:03.084282	2026-02-20 13:51:41.121227	\N	\N	\N
534	13617	Пластина токарная 22ER5.0TR DM215	19	1	\N	\N	2026-02-19 02:27:03.084582	2026-02-20 13:51:41.121227	\N	\N	\N
535	9616	Пластина токарная APKT11T308-APM IPM8520	40	4	\N	\N	2026-02-19 02:27:03.084845	2026-02-20 13:51:41.121227	\N	\N	\N
536	9610	Пластина токарная APKT11T308-GM CA5220	31	3	\N	\N	2026-02-19 02:27:03.085072	2026-02-20 13:51:41.121227	\N	\N	\N
537	10226	Пластина токарная APMT113504R-PM IA6330	53	5	\N	\N	2026-02-19 02:27:03.085315	2026-02-20 13:51:41.121227	\N	\N	\N
538	12606	Пластина токарная APMT1135PDER-HM-HR5130	128	12	\N	\N	2026-02-19 02:27:03.085583	2026-02-20 13:51:41.121227	\N	\N	\N
539	10970	Пластина токарная APMT160410-GM IA6330	129	12	\N	\N	2026-02-19 02:27:03.085823	2026-02-20 13:51:41.121227	\N	\N	\N
540	12605	Пластина токарная APMT1605PDER-HM-HR5120	30	3	\N	\N	2026-02-19 02:27:03.086097	2026-02-20 13:51:41.121227	\N	\N	\N
541	8298	Пластина токарная BP500 BPG20B	9	1	\N	\N	2026-02-19 02:27:03.08636	2026-02-20 13:51:41.121227	\N	\N	\N
542	13322	Пластина токарная CCMT060202-MM IA80M	18	1	\N	\N	2026-02-19 02:27:03.08663	2026-02-20 13:51:41.121227	\N	\N	\N
543	8284	Пластина токарная CCMT060208-FW BPS101	17	1	\N	\N	2026-02-19 02:27:03.086899	2026-02-20 13:51:41.121227	\N	\N	\N
544	17067	Пластина токарная CCMT09T304-MP-HS7125	10	1	\N	\N	2026-02-19 02:27:03.087143	2026-02-20 13:51:41.121227	\N	\N	\N
545	17068	Пластина токарная CCMT09T304-TM-HR8125	6	1	\N	\N	2026-02-19 02:27:03.087419	2026-02-20 13:51:41.121227	\N	\N	\N
546	17535	Пластина токарная CCMT120404-HMP-HR82512	8	1	\N	\N	2026-02-19 02:27:03.087678	2026-02-20 13:51:41.121227	\N	\N	\N
547	17536	Пластина токарная CCMT120412-ТМ-HR8125	10	1	\N	\N	2026-02-19 02:27:03.087926	2026-02-20 13:51:41.121227	\N	\N	\N
548	13324	Пластина токарная DCMT070202-TP AI80M	28	2	\N	\N	2026-02-19 02:27:03.088158	2026-02-20 13:51:41.121227	\N	\N	\N
549	13325	Пластина токарная DCMT070208-TP IA80M	6	1	\N	\N	2026-02-19 02:27:03.088396	2026-02-20 13:51:41.121227	\N	\N	\N
550	10972	Пластина токарная DCMT11T302-TP AI80M	45	4	\N	\N	2026-02-19 02:27:03.088677	2026-02-20 13:51:41.121227	\N	\N	\N
551	11821	Пластина токарная DCMT11T304-FP	20	2	\N	\N	2026-02-19 02:27:03.088971	2026-02-20 13:51:41.121227	\N	\N	\N
552	9998	Пластина токарная DCMT11T304-MT-MK6020	5	1	\N	\N	2026-02-19 02:27:03.08925	2026-02-20 13:51:41.121227	\N	\N	\N
553	14415	Пластина токарная DCMT11T308 LF9218	35	3	\N	\N	2026-02-19 02:27:03.089535	2026-02-20 13:51:41.121227	\N	\N	\N
554	22099	Пластина токарная DCMT11T308-GP IP4325	10	1	\N	\N	2026-02-19 02:27:03.089773	2026-02-20 13:51:41.121227	\N	\N	\N
555	16243	Пластина токарная DCMT11T308-MM IP4005	4	1	\N	\N	2026-02-19 02:27:03.09001	2026-02-20 13:51:41.121227	\N	\N	\N
556	15138	Пластина токарная DNMG150404-UF	8	1	\N	\N	2026-02-19 02:27:03.090259	2026-02-20 13:51:41.121227	\N	\N	\N
557	16395	Пластина токарная DNMG150404-XF	29	2	\N	\N	2026-02-19 02:27:03.090518	2026-02-20 13:51:41.121227	\N	\N	\N
558	13519	Пластина токарная DNMG150408-LR IM7325	69	6	\N	\N	2026-02-19 02:27:03.090759	2026-02-20 13:51:41.121227	\N	\N	\N
559	17301	Пластина токарная DNMG150408-XR MK6020	25	2	\N	\N	2026-02-19 02:27:03.090991	2026-02-20 13:51:41.121227	\N	\N	\N
560	16394	Пластина токарная DNMG150408-РР	4	1	\N	\N	2026-02-19 02:27:03.091227	2026-02-20 13:51:41.121227	\N	\N	\N
561	20750	Пластина токарная DNMG150608-TP IA80M	11	1	\N	\N	2026-02-19 02:27:03.091488	2026-02-20 13:51:41.121227	\N	\N	\N
562	7879	Пластина токарная DNMG150612-GR-HR8125	78	7	\N	\N	2026-02-19 02:27:03.09172	2026-02-20 13:51:41.121227	\N	\N	\N
563	10704	Пластина токарная DNMG150612-MD BPS371	30	3	\N	\N	2026-02-19 02:27:03.091966	2026-02-20 13:51:41.121227	\N	\N	\N
564	22098	Пластина токарная DNMG150612-MD YKH715	61	6	\N	\N	2026-02-19 02:27:03.092223	2026-02-20 13:51:41.121227	\N	\N	\N
565	10537	Пластина токарная GER100B PM125	10	1	\N	\N	2026-02-19 02:27:03.09248	2026-02-20 13:51:41.121227	\N	\N	\N
566	11743	Пластина токарная ITD4004-FG IS7025	5	1	\N	\N	2026-02-19 02:27:03.092739	2026-02-20 13:51:41.121227	\N	\N	\N
567	11747	Пластина токарная ITD6002-FG IS7025	6	1	\N	\N	2026-02-19 02:27:03.093002	2026-02-20 13:51:41.121227	\N	\N	\N
568	9600	Пластина токарная MGGN400-S06L PM310	8	1	\N	\N	2026-02-19 02:27:03.093252	2026-02-20 13:51:41.121227	\N	\N	\N
569	8956	Пластина токарная MGGN400-S06R PM310	5	1	\N	\N	2026-02-19 02:27:03.093503	2026-02-20 13:51:41.121227	\N	\N	\N
570	8958	Пластина токарная MGGN500-S06R DP510	30	3	\N	\N	2026-02-19 02:27:03.093757	2026-02-20 13:51:41.121227	\N	\N	\N
571	12673	Пластина токарная MGGN500-S06R PM310	21	2	\N	\N	2026-02-19 02:27:03.094019	2026-02-20 13:51:41.121227	\N	\N	\N
572	13523	Пластина токарная MGMN200-G PM310	41	4	\N	\N	2026-02-19 02:27:03.094287	2026-02-20 13:51:41.121227	\N	\N	\N
573	12091	Пластина токарная MGMN400-М PM310	38	3	\N	\N	2026-02-19 02:27:03.094566	2026-02-20 13:51:41.121227	\N	\N	\N
574	13524	Пластина токарная MRMN200-M PM310	49	4	\N	\N	2026-02-19 02:27:03.09486	2026-02-20 13:51:41.121227	\N	\N	\N
575	11828	Пластина токарная MRMN200-M PM315	10	1	\N	\N	2026-02-19 02:27:03.095173	2026-02-20 13:51:41.121227	\N	\N	\N
576	13842	Пластина токарная MTTR435502 DM215	10	1	\N	\N	2026-02-19 02:27:03.095434	2026-02-20 13:51:41.121227	\N	\N	\N
577	11831	Пластина токарная RCMT1204MOE-R2	17	1	\N	\N	2026-02-19 02:27:03.095669	2026-02-20 13:51:41.121227	\N	\N	\N
578	13576	Пластина токарная RPEW1003MO CA5020	8	1	\N	\N	2026-02-19 02:27:03.095904	2026-02-20 13:51:41.121227	\N	\N	\N
579	16241	Пластина токарная RPМW1003MOТ BPG20B	10	1	\N	\N	2026-02-19 02:27:03.096199	2026-02-20 13:51:41.121227	\N	\N	\N
580	11820	Пластина токарная SNMG120404-SM	10	1	\N	\N	2026-02-19 02:27:03.096499	2026-02-20 13:51:41.121227	\N	\N	\N
581	11829	Пластина токарная SPDR150DM10	21	2	\N	\N	2026-02-19 02:27:03.096781	2026-02-20 13:51:41.121227	\N	\N	\N
582	11318	Пластина токарная SPDR200DM10	20	2	\N	\N	2026-02-19 02:27:03.097039	2026-02-20 13:51:41.121227	\N	\N	\N
583	11319	Пластина токарная SPDR250DM10	10	1	\N	\N	2026-02-19 02:27:03.097291	2026-02-20 13:51:41.121227	\N	\N	\N
584	11320	Пластина токарная SPDR300DM10	10	1	\N	\N	2026-02-19 02:27:03.097556	2026-02-20 13:51:41.121227	\N	\N	\N
585	13360	Пластина токарная SPGT060204-SPM 	50	5	\N	\N	2026-02-19 02:27:03.097811	2026-02-20 13:51:41.121227	\N	\N	\N
586	13357	Пластина токарная SPGT090408-SPM 	32	3	\N	\N	2026-02-19 02:27:03.098056	2026-02-20 13:51:41.121227	\N	\N	\N
587	17981	Пластина токарная SPGT140512-SPM ST9015 (наружняя)	10	1	\N	\N	2026-02-19 02:27:03.09831	2026-02-20 13:51:41.121227	\N	\N	\N
588	17982	Пластина токарная SPGT140512-SPM ST9110 (внутренняя)	10	1	\N	\N	2026-02-19 02:27:03.098595	2026-02-20 13:51:41.121227	\N	\N	\N
589	14037	Пластина токарная TBGT060102L- IA80F	10	1	\N	\N	2026-02-19 02:27:03.098857	2026-02-20 13:51:41.121227	\N	\N	\N
590	16236	Пластина токарная TCMT090204-TP IA80M	12	1	\N	\N	2026-02-19 02:27:03.099155	2026-02-20 13:51:41.121227	\N	\N	\N
591	10948	Пластина токарная TCMT090208-TP IA80M	30	3	\N	\N	2026-02-19 02:27:03.099417	2026-02-20 13:51:41.121227	\N	\N	\N
592	8607	Пластина токарная TDC4-HS7225	22	2	\N	\N	2026-02-19 02:27:03.099678	2026-02-20 13:51:41.121227	\N	\N	\N
593	8330	Пластина токарная TDC5-HS7225	8	1	\N	\N	2026-02-19 02:27:03.099942	2026-02-20 13:51:41.121227	\N	\N	\N
594	18742	Пластина токарная TPGH110302L-P IA80F	10	1	\N	\N	2026-02-19 02:27:03.100217	2026-02-20 13:51:41.121227	\N	\N	\N
595	8286	Пластина токарная TPMH090202-FV VP15TF	9	1	\N	\N	2026-02-19 02:27:03.100516	2026-02-20 13:51:41.121227	\N	\N	\N
596	14484	Пластина токарная VBMT160404-GP IP4015	29	2	\N	\N	2026-02-19 02:27:03.100791	2026-02-20 13:51:41.121227	\N	\N	\N
597	14485	Пластина токарная VBMT160404-MM IA80M	59	5	\N	\N	2026-02-19 02:27:03.101047	2026-02-20 13:51:41.121227	\N	\N	\N
598	10707	Пластина токарная VNMG160404-LM IM7425	60	6	\N	\N	2026-02-19 02:27:03.101297	2026-02-20 13:51:41.121227	\N	\N	\N
599	13616	Пластина токарная VNMG160404-MM IA80M	40	4	\N	\N	2026-02-19 02:27:03.101566	2026-02-20 13:51:41.121227	\N	\N	\N
600	11734	Пластина токарная VNMG160404-SF IS7015	4	1	\N	\N	2026-02-19 02:27:03.101831	2026-02-20 13:51:41.121227	\N	\N	\N
601	16966	Пластина токарная WNMA 080412 IK4025	28	2	\N	\N	2026-02-19 02:27:03.102104	2026-02-20 13:51:41.121227	\N	\N	\N
602	11749	Пластина токарная ZPGS0402-MG IP7120	7	1	\N	\N	2026-02-19 02:27:03.102353	2026-02-20 13:51:41.121227	\N	\N	\N
603	8138	Пластина токарная ZTHD0504-MG HR52522	7	1	\N	\N	2026-02-19 02:27:03.102621	2026-02-20 13:51:41.121227	\N	\N	\N
604	10539	Пластина токарная внутренняя SPGT07T308-SPM ST9110	45	4	\N	\N	2026-02-19 02:27:03.102889	2026-02-20 13:51:41.121227	\N	\N	\N
605	8294	Пластина токарная МPHT060304-DM CA5220	30	3	\N	\N	2026-02-19 02:27:03.103166	2026-02-20 13:51:41.121227	\N	\N	\N
606	8293	Пластина токарная МPHT060304-M DM215	20	2	\N	\N	2026-02-19 02:27:03.10346	2026-02-20 13:51:41.121227	\N	\N	\N
607	11822	Пластина токарная МТТR436001 DM215 	30	3	\N	\N	2026-02-19 02:27:03.103765	2026-02-20 13:51:41.121227	\N	\N	\N
608	11824	Пластина токарная МТТR436003 DM215	12	1	\N	\N	2026-02-19 02:27:03.104066	2026-02-20 13:51:41.121227	\N	\N	\N
609	10540	Пластина токарная наружняя SPGT07T308-SPM ST9015	35	3	\N	\N	2026-02-19 02:27:03.104352	2026-02-20 13:51:41.121227	\N	\N	\N
610	11909	Пластина токарная твердосплавная IG4150L-020 IA6330	15	1	\N	\N	2026-02-19 02:27:03.104674	2026-02-20 13:51:41.121227	\N	\N	\N
611	4216	Плашка М10*1,25	10	1	\N	\N	2026-02-19 02:27:03.104951	2026-02-20 13:51:41.121227	\N	\N	\N
612	3575	Плашка М10*1,5	9	1	\N	\N	2026-02-19 02:27:03.105296	2026-02-20 13:51:41.121227	\N	\N	\N
613	3577	Плашка М14*1,5	7	1	\N	\N	2026-02-19 02:27:03.105585	2026-02-20 13:51:41.121227	\N	\N	\N
614	22446	Развертка машинная 10.5х38х133	5	1	\N	\N	2026-02-19 02:27:03.10589	2026-02-20 13:51:41.121227	\N	\N	\N
615	22547	Развертка машинная 18,0 Н11	5	1	\N	\N	2026-02-19 02:27:03.106242	2026-02-20 13:51:41.121227	\N	\N	\N
616	22587	Развертка машинная 18,0 Н8	3	1	\N	\N	2026-02-19 02:27:03.106601	2026-02-20 13:51:41.121227	\N	\N	\N
617	22460	Развертка машинная U8 М25*19*220	3	1	\N	\N	2026-02-19 02:27:03.106838	2026-02-20 13:51:41.121227	\N	\N	\N
618	20952	Развертка машинная М12*18*150	2	1	\N	\N	2026-02-19 02:27:03.107086	2026-02-20 13:51:41.121227	\N	\N	\N
619	20729	Развертка машинная М12*40*75	2	1	\N	\N	2026-02-19 02:27:03.107351	2026-02-20 13:51:41.121227	\N	\N	\N
620	21786	Развертка машинная М15*50*100	4	1	\N	\N	2026-02-19 02:27:03.107612	2026-02-20 13:51:41.121227	\N	\N	\N
621	14508	Развертка машинная М16*50*100	2	1	\N	\N	2026-02-19 02:27:03.107869	2026-02-20 13:51:41.121227	\N	\N	\N
622	1237	Развертка машинная М18 Н10	5	1	\N	\N	2026-02-19 02:27:03.10813	2026-02-20 13:51:41.121227	\N	\N	\N
623	13139	Развертка машинная М18*56*182 Н7	5	1	\N	\N	2026-02-19 02:27:03.108403	2026-02-20 13:51:41.121227	\N	\N	\N
624	20964	Развертка машинная М25*22*220	4	1	\N	\N	2026-02-19 02:27:03.108663	2026-02-20 13:51:41.121227	\N	\N	\N
625	20728	Развертка машинная М25*68*268	2	1	\N	\N	2026-02-19 02:27:03.108943	2026-02-20 13:51:41.121227	\N	\N	\N
626	21307	Развертка ручная 35,0-40,0 (регулируемая)	2	1	\N	\N	2026-02-19 02:27:03.109176	2026-02-20 13:51:41.121227	\N	\N	\N
627	13780	Развертка ручная М18	12	1	\N	\N	2026-02-19 02:27:03.109416	2026-02-20 13:51:41.121227	\N	\N	\N
628	21306	Развертка ручная М8 Н10	10	1	\N	\N	2026-02-19 02:27:03.109701	2026-02-20 13:51:41.121227	\N	\N	\N
629	21305	Развертка ручная М8 Н7	9	1	\N	\N	2026-02-19 02:27:03.109939	2026-02-20 13:51:41.121227	\N	\N	\N
630	22091	Раскатник TA02R01215 HSS-E M12x1.5 6H, TiALN (TICN-C)	8	1	\N	\N	2026-02-19 02:27:03.110207	2026-02-20 13:51:41.121227	\N	\N	\N
631	7138	Резец DVVNN2020M16	3	1	\N	\N	2026-02-19 02:27:03.110511	2026-02-20 13:51:41.121227	\N	\N	\N
632	10526	Резец DVVNN2525M16	1	1	\N	\N	2026-02-19 02:27:03.110753	2026-02-20 13:51:41.121227	\N	\N	\N
633	11467	Резец канавочный торцевой QFGD2525L22-130L	3	1	\N	\N	2026-02-19 02:27:03.110991	2026-02-20 13:51:41.121227	\N	\N	\N
354	15367	Державка MGEHL2525-2	12	1	\N	\N	2026-02-19 02:27:03.001841	2026-02-20 13:51:41.121227	\N	\N	\N
355	13522	Державка MGEHR2525-2	7	1	\N	\N	2026-02-19 02:27:03.002443	2026-02-20 13:51:41.121227	\N	\N	\N
356	10821	Державка MVQNL2525M16	13	1	\N	\N	2026-02-19 02:27:03.00301	2026-02-20 13:51:41.121227	\N	\N	\N
357	13521	Державка MVQNR2525M16	7	1	\N	\N	2026-02-19 02:27:03.00359	2026-02-20 13:51:41.121227	\N	\N	\N
358	10004	Державка PCBNR 2525 M12C	2	1	\N	\N	2026-02-19 02:27:03.004219	2026-02-20 13:51:41.121227	\N	\N	\N
359	11300	Державка QFGD2525L22-90H	1	1	\N	\N	2026-02-19 02:27:03.004893	2026-02-20 13:51:41.121227	\N	\N	\N
360	11304	Державка QXFD2525R03-45	1	1	\N	\N	2026-02-19 02:27:03.005534	2026-02-20 13:51:41.121227	\N	\N	\N
361	16269	Державка S10K-SDUCR07	1	1	\N	\N	2026-02-19 02:27:03.0061	2026-02-20 13:51:41.121227	\N	\N	\N
362	16270	Державка S10M-SDUCR07	4	1	\N	\N	2026-02-19 02:27:03.006613	2026-02-20 13:51:41.121227	\N	\N	\N
363	22746	Державка S40T-MVQNR16	1	1	\N	\N	2026-02-19 02:27:03.007089	2026-02-20 13:51:41.121227	\N	\N	\N
364	8327	Державка SNR0010K11	3	1	\N	\N	2026-02-19 02:27:03.007555	2026-02-20 13:51:41.121227	\N	\N	\N
365	22554	Державка TTIL20-3C	2	1	\N	\N	2026-02-19 02:27:03.008026	2026-02-20 13:51:41.121227	\N	\N	\N
366	22630	Державка для полировки 25*25	1	1	\N	\N	2026-02-19 02:27:03.008505	2026-02-20 13:51:41.121227	\N	\N	\N
367	11294	Державка канавочная SIGER0025R-E	1	1	\N	\N	2026-02-19 02:27:03.00899	2026-02-20 13:51:41.121227	\N	\N	\N
368	10536	Державка канавочная SIGER1010B-WH	3	1	\N	\N	2026-02-19 02:27:03.009472	2026-02-20 13:51:41.121227	\N	\N	\N
369	20569	Державка токарная A40T-DDUNR	1	1	\N	\N	2026-02-19 02:27:03.009957	2026-02-20 13:51:41.121227	\N	\N	\N
370	13320	Державка токарная C08K-SCLCR06	1	1	\N	\N	2026-02-19 02:27:03.010485	2026-02-20 13:51:41.121227	\N	\N	\N
371	13323	Державка токарная C10M-SDQCR07	2	1	\N	\N	2026-02-19 02:27:03.010994	2026-02-20 13:51:41.121227	\N	\N	\N
372	10229	Державка токарная E08K-SCLCR06	1	1	\N	\N	2026-02-19 02:27:03.011511	2026-02-20 13:51:41.121227	\N	\N	\N
373	11922	Державка токарная IGEL2525M415 	5	1	\N	\N	2026-02-19 02:27:03.012051	2026-02-20 13:51:41.121227	\N	\N	\N
374	8954	Державка токарная IKER2525-4Т25	12	1	\N	\N	2026-02-19 02:27:03.01254	2026-02-20 13:51:41.121227	\N	\N	\N
375	14861	Державка токарная ITIR2016-2T04	9	1	\N	\N	2026-02-19 02:27:03.013053	2026-02-20 13:51:41.121227	\N	\N	\N
376	9625	Державка токарная ITIR3125-4T06	1	1	\N	\N	2026-02-19 02:27:03.0136	2026-02-20 13:51:41.121227	\N	\N	\N
377	20570	Державка токарная ITIR4740-5T10	1	1	\N	\N	2026-02-19 02:27:03.014127	2026-02-20 13:51:41.121227	\N	\N	\N
353	11830	Державка KSPDR0016K10	12	1	Державка	\N	2026-02-19 02:27:03.001248	2026-03-03 08:29:39.121449	https://wolfstar.ru/thumb/2/Z_lZB9bCgG68dVTSRhrSXA/r/d/kspdr0016f10_1.jpg	https://wolfstar.ru/magazin/product/derzhavka-dlya-torcevyh-kanavok-kspdr0016f10-panda-cnc	{"Вид точения": "Канавочный"}
350	16271	Державка A16Q-SDUCR11	5	1	Державка	\N	2026-02-19 02:27:02.998534	2026-03-02 12:43:59.086461	https://cncmagazine.ru/images/detailed/43/SDUCR_15qq-ib.jpg	https://cncmagazine.ru/rezcy-so-smennymi-plastinami/rastochnye-opravki/a16q-sducr11-derzhavka/	{"Вид точения": "Внутреннее"}
351	10820	Державка DDJNL2525M15	5	1	Державка	\N	2026-02-19 02:27:02.999745	2026-03-02 12:45:51.906607	https://cncmagazine.ru/images/detailed/54/DDJNL_6had-2m.jpg	https://cncmagazine.ru/rezcy-so-smennymi-plastinami/rezcy-dlya-naruzhnogo-tocheniya/ddjnl2525m15/	{"Вид точения": "наружное"}
352	13520	Державка DDJNR2525M15	8	1	Державка	\N	2026-02-19 02:27:03.000411	2026-03-02 12:46:36.924208	https://cncmagazine.ru/images/detailed/54/DDJNR_9t74-8z.jpg	https://cncmagazine.ru/rezcy-so-smennymi-plastinami/rezcy-dlya-naruzhnogo-tocheniya/ddjnr2525m15/	{"Вид точения": "наружное"}
349	16272	A16Q-SDQCR11 державка расточная	25	5	Державка	\N	2026-02-19 02:27:02.996676	2026-04-20 08:33:17.662236	https://cncmagazine.ru/images/detailed/22/SDQC-d.jpg	https://cncmagazine.ru/rezcy-so-smennymi-plastinami/rastochnye-opravki/a16q-sdqcr11-derzhavka/	{"Вид точения": "Внутреннее", "Тип державки": "Стальная с каналом для СОЖ", "d хвостовика": "16мм", "D min": "20мм", "Длинна L": "180 (Q) мм", "Размер устанвливаемой пластины": "D-ромбическая 55°", "e": "30 мм", "h": "15 мм", "S": "11 мм"}
930	000000	Сверло корпус UD30.SP07.240.W25	2	1	Сверло	\N	2026-04-23 07:28:58.175635	2026-04-23 07:28:58.175647	\N	\N	\N
391	9794	Держатель инструмента В6-40*25*44	1	1	\N	\N	2026-02-19 02:27:03.021702	2026-02-20 13:51:41.121227	\N	\N	\N
634	8706	Резец канавочный торцевой QFGD2525L22-52L	1	1	\N	\N	2026-02-19 02:27:03.11126	2026-02-20 13:51:41.121227	\N	\N	\N
635	8606	Резец расточной C40T-QGDL.13-54	2	1	\N	\N	2026-02-19 02:27:03.111505	2026-02-20 13:51:41.121227	\N	\N	\N
636	16296	Резец расточной S25R-MVXNR16	5	1	\N	\N	2026-02-19 02:27:03.111788	2026-02-20 13:51:41.121227	\N	\N	\N
637	9897	Резец токарный EVJNL2525M16	1	1	\N	\N	2026-02-19 02:27:03.112066	2026-02-20 13:51:41.121227	\N	\N	\N
638	9898	Резец токарный MVUNR2525M16	2	1	\N	\N	2026-02-19 02:27:03.112333	2026-02-20 13:51:41.121227	\N	\N	\N
639	9847	Резьбофреза D1MT080800D18-60 BR205	3	1	\N	\N	2026-02-19 02:27:03.112595	2026-02-20 13:51:41.121227	\N	\N	\N
640	9848	Резьбофреза D1MT101000D26-60 BR205	2	1	\N	\N	2026-02-19 02:27:03.112869	2026-02-20 13:51:41.121227	\N	\N	\N
641	9619	Резьбофреза D1MT121200D30-60 BR205	4	1	\N	\N	2026-02-19 02:27:03.113129	2026-02-20 13:51:41.121227	\N	\N	\N
688	10967	Сверло DM861-5С-1050	4	1	\N	\N	2026-02-19 02:27:03.137201	2026-02-20 13:51:41.121227	\N	\N	\N
689	15130	Сверло DPP447100 10*10*45*80	2	1	\N	\N	2026-02-19 02:27:03.137459	2026-02-20 13:51:41.121227	\N	\N	\N
690	21004	Сверло UD20.SP07.250.W25	3	1	\N	\N	2026-02-19 02:27:03.137719	2026-02-20 13:51:41.121227	\N	\N	\N
692	21130	Сверло UD30.SP07.250.W32	1	1	\N	\N	2026-02-19 02:27:03.138245	2026-02-20 13:51:41.121227	\N	\N	\N
693	13355	Сверло UD30.SP09.325.W32	2	1	\N	\N	2026-02-19 02:27:03.138493	2026-02-20 13:51:41.121227	\N	\N	\N
694	15425	Сверло UD30.WC08.550.W40	1	1	\N	\N	2026-02-19 02:27:03.138735	2026-02-20 13:51:41.121227	\N	\N	\N
695	12664	Сверло UD40.SP06.180.W25	1	1	\N	\N	2026-02-19 02:27:03.138989	2026-02-20 13:51:41.121227	\N	\N	\N
696	12504	Сверло UD50.SP06.180.W25	1	1	\N	\N	2026-02-19 02:27:03.139265	2026-02-20 13:51:41.121227	\N	\N	\N
697	16239	Сверло UD50.SP06.200.W25	8	1	\N	\N	2026-02-19 02:27:03.139508	2026-02-20 13:51:41.121227	\N	\N	\N
698	11577	Сверло UD50.SP07.250.W25	2	1	\N	\N	2026-02-19 02:27:03.139757	2026-02-20 13:51:41.121227	\N	\N	\N
699	17980	Сверло UD50.SP14.500.W40	1	1	\N	\N	2026-02-19 02:27:03.140055	2026-02-20 13:51:41.121227	\N	\N	\N
700	9145	Сверло по металлу 3,5мм CCD5035	3	1	\N	\N	2026-02-19 02:27:03.14033	2026-02-20 13:51:41.121227	\N	\N	\N
701	20983	Сверло по металлу к/х 11,5	3	1	\N	\N	2026-02-19 02:27:03.140601	2026-02-20 13:51:41.121227	\N	\N	\N
702	18613	Сверло по металлу к/х 18,0	10	1	\N	\N	2026-02-19 02:27:03.140862	2026-02-20 13:51:41.121227	\N	\N	\N
703	20981	Сверло по металлу к/х 40	2	1	\N	\N	2026-02-19 02:27:03.141136	2026-02-20 13:51:41.121227	\N	\N	\N
704	9940	Сверло по металлу кобальтовое ц/х 10	7	1	\N	\N	2026-02-19 02:27:03.141448	2026-02-20 13:51:41.121227	\N	\N	\N
705	12535	Сверло по металлу кобальтовое ц/х 10,5	16	1	\N	\N	2026-02-19 02:27:03.141727	2026-02-20 13:51:41.121227	\N	\N	\N
706	12531	Сверло по металлу кобальтовое ц/х 11,0	15	1	\N	\N	2026-02-19 02:27:03.142004	2026-02-20 13:51:41.121227	\N	\N	\N
707	12541	Сверло по металлу кобальтовое ц/х 11,5	12	1	\N	\N	2026-02-19 02:27:03.142293	2026-02-20 13:51:41.121227	\N	\N	\N
708	11895	Сверло по металлу кобальтовое ц/х 12,0	4	1	\N	\N	2026-02-19 02:27:03.142573	2026-02-20 13:51:41.121227	\N	\N	\N
709	12540	Сверло по металлу кобальтовое ц/х 12,5	24	2	\N	\N	2026-02-19 02:27:03.142833	2026-02-20 13:51:41.121227	\N	\N	\N
710	16856	Сверло по металлу кобальтовое ц/х 13,0	8	1	\N	\N	2026-02-19 02:27:03.143095	2026-02-20 13:51:41.121227	\N	\N	\N
711	13319	Сверло по металлу кобальтовое ц/х 13,1	14	1	\N	\N	2026-02-19 02:27:03.143355	2026-02-20 13:51:41.121227	\N	\N	\N
712	12539	Сверло по металлу кобальтовое ц/х 13,5	9	1	\N	\N	2026-02-19 02:27:03.143618	2026-02-20 13:51:41.121227	\N	\N	\N
713	12519	Сверло по металлу кобальтовое ц/х 13,9	7	1	\N	\N	2026-02-19 02:27:03.143917	2026-02-20 13:51:41.121227	\N	\N	\N
714	9710	Сверло по металлу кобальтовое ц/х 14,0	4	1	\N	\N	2026-02-19 02:27:03.14421	2026-02-20 13:51:41.121227	\N	\N	\N
715	12538	Сверло по металлу кобальтовое ц/х 14,5	2	1	\N	\N	2026-02-19 02:27:03.144523	2026-02-20 13:51:41.121227	\N	\N	\N
716	13135	Сверло по металлу кобальтовое ц/х 15	2	1	\N	\N	2026-02-19 02:27:03.144849	2026-02-20 13:51:41.121227	\N	\N	\N
717	14414	Сверло по металлу кобальтовое ц/х 15,5	10	1	\N	\N	2026-02-19 02:27:03.145156	2026-02-20 13:51:41.121227	\N	\N	\N
718	12532	Сверло по металлу кобальтовое ц/х 16,0	12	1	\N	\N	2026-02-19 02:27:03.145479	2026-02-20 13:51:41.121227	\N	\N	\N
691	14601	Фреза IH30-1010-25075-R6	3	1	\N	\N	2026-02-19 02:27:03.137985	2026-02-20 13:51:41.121227	\N	\N	\N
719	13136	Сверло по металлу кобальтовое ц/х 16,5	9	1	\N	\N	2026-02-19 02:27:03.145757	2026-02-20 13:51:41.121227	\N	\N	\N
720	12533	Сверло по металлу кобальтовое ц/х 17,0	7	1	\N	\N	2026-02-19 02:27:03.146118	2026-02-20 13:51:41.121227	\N	\N	\N
721	12534	Сверло по металлу кобальтовое ц/х 17,5	11	1	\N	\N	2026-02-19 02:27:03.146426	2026-02-20 13:51:41.121227	\N	\N	\N
722	12536	Сверло по металлу кобальтовое ц/х 19,0	5	1	\N	\N	2026-02-19 02:27:03.146737	2026-02-20 13:51:41.121227	\N	\N	\N
723	12537	Сверло по металлу кобальтовое ц/х 20,0	6	1	\N	\N	2026-02-19 02:27:03.147027	2026-02-20 13:51:41.121227	\N	\N	\N
724	22744	Сверло по металлу кобальтовое ц/х 3,4	5	1	\N	\N	2026-02-19 02:27:03.147305	2026-02-20 13:51:41.121227	\N	\N	\N
725	10085	Сверло по металлу кобальтовое ц/х 4,0	8	1	\N	\N	2026-02-19 02:27:03.147595	2026-02-20 13:51:41.121227	\N	\N	\N
726	10089	Сверло по металлу кобальтовое ц/х 5,0	12	1	\N	\N	2026-02-19 02:27:03.147951	2026-02-20 13:51:41.121227	\N	\N	\N
727	9296	Сверло по металлу кобальтовое ц/х 6,0	6	1	\N	\N	2026-02-19 02:27:03.148334	2026-02-20 13:51:41.121227	\N	\N	\N
728	9703	Сверло по металлу кобальтовое ц/х 7,0	8	1	\N	\N	2026-02-19 02:27:03.148624	2026-02-20 13:51:41.121227	\N	\N	\N
729	9297	Сверло по металлу кобальтовое ц/х 8,0	6	1	\N	\N	2026-02-19 02:27:03.148905	2026-02-20 13:51:41.121227	\N	\N	\N
730	12530	Сверло по металлу кобальтовое ц/х 9,0	13	1	\N	\N	2026-02-19 02:27:03.149183	2026-02-20 13:51:41.121227	\N	\N	\N
731	20802	Сверло по металлу удлиненное к/х 12*210*300	7	1	\N	\N	2026-02-19 02:27:03.149457	2026-02-20 13:51:41.121227	\N	\N	\N
732	20803	Сверло по металлу удлиненное к/х 14*210*300	6	1	\N	\N	2026-02-19 02:27:03.149729	2026-02-20 13:51:41.121227	\N	\N	\N
733	13024	Сверло по металлу удлиненное к/х 16*300*520	2	1	\N	\N	2026-02-19 02:27:03.149999	2026-02-20 13:51:41.121227	\N	\N	\N
734	13071	Сверло по металлу удлиненное к/х 23*250*350	3	1	\N	\N	2026-02-19 02:27:03.150262	2026-02-20 13:51:41.121227	\N	\N	\N
735	20953	Сверло по металлу удлиненное к/х 24,5*190*345	1	1	\N	\N	2026-02-19 02:27:03.150559	2026-02-20 13:51:41.121227	\N	\N	\N
736	21132	Сверло по металлу удлиненное к/х 50*220*369	1	1	\N	\N	2026-02-19 02:27:03.150822	2026-02-20 13:51:41.121227	\N	\N	\N
737	21345	Сверло по металлу удлиненное ц/х 1,2*41*65	30	3	\N	\N	2026-02-19 02:27:03.15108	2026-02-20 13:51:41.121227	\N	\N	\N
738	20963	Сверло по металлу удлиненное ц/х 4*210*300	2	1	\N	\N	2026-02-19 02:27:03.151332	2026-02-20 13:51:41.121227	\N	\N	\N
739	11906	Сверло по металлу ц/х 1,5	16	1	\N	\N	2026-02-19 02:27:03.151605	2026-02-20 13:51:41.121227	\N	\N	\N
740	3226	Сверло по металлу ц/х 2,5	8	1	\N	\N	2026-02-19 02:27:03.151899	2026-02-20 13:51:41.121227	\N	\N	\N
741	12666	Сверло СА55-3-0900	8	1	\N	\N	2026-02-19 02:27:03.152169	2026-02-20 13:51:41.121227	\N	\N	\N
742	11311	Сверло СА55-5-0400	6	1	\N	\N	2026-02-19 02:27:03.152431	2026-02-20 13:51:41.121227	\N	\N	\N
743	10583	Сверло СА55-5-0420	4	1	\N	\N	2026-02-19 02:27:03.15269	2026-02-20 13:51:41.121227	\N	\N	\N
744	16377	Сверло со сменной пластиной GSD-175-03D-FC25-S	2	1	\N	\N	2026-02-19 02:27:03.152938	2026-02-20 13:51:41.121227	\N	\N	\N
745	14036	Сверло со сменной пластиной GSD-175-05D-FC25	3	1	\N	\N	2026-02-19 02:27:03.153206	2026-02-20 13:51:41.121227	\N	\N	\N
746	22601	Сверло спиральное ц/х HSS-Co 13х151 мм DIN338¶М35 хв.13х25,4 (Р6М5К5)	10	1	\N	\N	2026-02-19 02:27:03.153451	2026-02-20 13:51:41.121227	\N	\N	\N
747	10966	Сверло твердосплавное 10мм	1	1	\N	\N	2026-02-19 02:27:03.153694	2026-02-20 13:51:41.121227	\N	\N	\N
748	10917	Сверло твердосплавное 7мм 	18	1	\N	\N	2026-02-19 02:27:03.153953	2026-02-20 13:51:41.121227	\N	\N	\N
749	22823	Сверло твердосплавное DH2231000 10X10X47X89	1	1	\N	\N	2026-02-19 02:27:03.154223	2026-02-20 13:51:41.121227	\N	\N	\N
750	23298	Сверло твердосплавное DH2240520 5.2*6*44*82	2	1	\N	\N	2026-02-19 02:27:03.154498	2026-02-20 13:51:41.121227	\N	\N	\N
751	17500	Сверло твердосплавное по металлу 10,5 DPMK1.105.12.37.102 TiAIN	8	1	\N	\N	2026-02-19 02:27:03.154774	2026-02-20 13:51:41.121227	\N	\N	\N
752	9147	Сверло твердосплавное по металлу 10мм CCD5100	2	1	\N	\N	2026-02-19 02:27:03.155052	2026-02-20 13:51:41.121227	\N	\N	\N
753	14621	Сверло твердосплавное по металлу 11.3 DPMK1.113.12.55.102 TiAlN	12	1	\N	\N	2026-02-19 02:27:03.155324	2026-02-20 13:51:41.121227	\N	\N	\N
754	7726	Сверло твердосплавное по металлу 12 BD05CA1200-HF35	1	1	\N	\N	2026-02-19 02:27:03.155585	2026-02-20 13:51:41.121227	\N	\N	\N
755	7727	Сверло твердосплавное по металлу 12 BD08CA1200-HF35	2	1	\N	\N	2026-02-19 02:27:03.155872	2026-02-20 13:51:41.121227	\N	\N	\N
756	22101	Сверло твердосплавное по металлу 12 DA81-3-1200	3	1	\N	\N	2026-02-19 02:27:03.156259	2026-02-20 13:51:41.121227	\N	\N	\N
757	22100	Сверло твердосплавное по металлу 12 DA83-5C-1200	3	1	\N	\N	2026-02-19 02:27:03.156508	2026-02-20 13:51:41.121227	\N	\N	\N
758	8338	Сверло твердосплавное по металлу 3,5 BD05CA0350-HF35	3	1	\N	\N	2026-02-19 02:27:03.156784	2026-02-20 13:51:41.121227	\N	\N	\N
759	8780	Сверло твердосплавное по металлу 3,7 DPMK1.037.06.11.62.TiAIN	2	1	\N	\N	2026-02-19 02:27:03.157052	2026-02-20 13:51:41.121227	\N	\N	\N
760	11308	Сверло твердосплавное по металлу 4,2*22*55	2	1	\N	\N	2026-02-19 02:27:03.157337	2026-02-20 13:51:41.121227	\N	\N	\N
761	8781	Сверло твердосплавное по металлу 4,7	6	1	\N	\N	2026-02-19 02:27:03.157599	2026-02-20 13:51:41.121227	\N	\N	\N
762	11310	Сверло твердосплавное по металлу 4*22*55	8	1	\N	\N	2026-02-19 02:27:03.157856	2026-02-20 13:51:41.121227	\N	\N	\N
763	8137	Сверло твердосплавное по металлу 6 BD08CA0600-HF35	1	1	\N	\N	2026-02-19 02:27:03.15811	2026-02-20 13:51:41.121227	\N	\N	\N
764	10919	Сверло твердосплавное по металлу 7,5 DPMK1.075.08.46.91.TiAIN	6	1	\N	\N	2026-02-19 02:27:03.15838	2026-02-20 13:51:41.121227	\N	\N	\N
765	17499	Сверло твердосплавное по металлу 7,8 DPMK1.078.08.29.79.TiAIN	9	1	\N	\N	2026-02-19 02:27:03.158646	2026-02-20 13:51:41.121227	\N	\N	\N
766	8602	Сверло твердосплавное по металлу 8	3	1	\N	\N	2026-02-19 02:27:03.158926	2026-02-20 13:51:41.121227	\N	\N	\N
767	8601	Сверло твердосплавное по металлу 8 BD05CA0800-HF35	2	1	\N	\N	2026-02-19 02:27:03.159191	2026-02-20 13:51:41.121227	\N	\N	\N
768	15364	Сверло твердосплавное по металлу 8,5 DPMK1.085.10.32.89 TiAIN	5	1	\N	\N	2026-02-19 02:27:03.159467	2026-02-20 13:51:41.121227	\N	\N	\N
769	9899	Сверло твердосплавное по металлу 9 BD05CA0900-HF35	3	1	\N	\N	2026-02-19 02:27:03.15978	2026-02-20 13:51:41.121227	\N	\N	\N
770	11049	Сверло твердосплавное по металлу 9,4 DPMK1.094.10.51.102.TiAIN	10	1	\N	\N	2026-02-19 02:27:03.160076	2026-02-20 13:51:41.121227	\N	\N	\N
771	8785	Сверло твердосплавное по металлу 9,5 DPMK1.095.10.32.89.TiAIN	1	1	\N	\N	2026-02-19 02:27:03.160362	2026-02-20 13:51:41.121227	\N	\N	\N
772	10921	Сверло твердосплавное по металлу 9,5 DPMK1.095.10.51.102.TiAIN	5	1	\N	\N	2026-02-19 02:27:03.16066	2026-02-20 13:51:41.121227	\N	\N	\N
773	6095	Сверло ф18 Р6М5	8	1	\N	\N	2026-02-19 02:27:03.160945	2026-02-20 13:51:41.121227	\N	\N	\N
774	6094	Сверло ф18,5 Р6М5	10	1	\N	\N	2026-02-19 02:27:03.161317	2026-02-20 13:51:41.121227	\N	\N	\N
775	9705	Сверло центровочное 2,5	1	1	\N	\N	2026-02-19 02:27:03.16158	2026-02-20 13:51:41.121227	\N	\N	\N
776	21128	Сверло центровочное 3,15*8*50	17	1	\N	\N	2026-02-19 02:27:03.161881	2026-02-20 13:51:41.121227	\N	\N	\N
777	13697	Сверло центровочное 4*10*5*56	9	1	\N	\N	2026-02-19 02:27:03.162162	2026-02-20 13:51:41.121227	\N	\N	\N
778	11292	Сверло центровочное 5*12,5*63	17	1	\N	\N	2026-02-19 02:27:03.162423	2026-02-20 13:51:41.121227	\N	\N	\N
779	9704	Сверло центровочное 6,3	10	1	\N	\N	2026-02-19 02:27:03.162706	2026-02-20 13:51:41.121227	\N	\N	\N
780	20469	Фреза 1Z*6*25 AL	2	1	\N	\N	2026-02-19 02:27:03.162971	2026-02-20 13:51:41.121227	\N	\N	\N
781	20207	Фреза 2Z*2.5*15	1	1	\N	\N	2026-02-19 02:27:03.163233	2026-02-20 13:51:41.121227	\N	\N	\N
782	12448	Фреза 3-х зубая концевая N93.Z3.12.45.100.45.F030	1	1	\N	\N	2026-02-19 02:27:03.163502	2026-02-20 13:51:41.121227	\N	\N	\N
783	15120	Фреза 4-х зубая концевая G8А02050 5*6*5(13)*55*5070	6	1	\N	\N	2026-02-19 02:27:03.163766	2026-02-20 13:51:41.121227	\N	\N	\N
784	15122	Фреза 4-х зубая концевая G9432050 5*5*14*50	1	1	\N	\N	2026-02-19 02:27:03.164027	2026-02-20 13:51:41.121227	\N	\N	\N
785	22096	Фреза 4-х зубая концевая G9J24025N 2.5*4*8*50 Alpha-MX 	6	1	\N	\N	2026-02-19 02:27:03.164294	2026-02-20 13:51:41.121227	\N	\N	\N
786	12450	Фреза 4-х зубая кромочная PMK41.z4.10.XX.72.SF90	6	1	\N	\N	2026-02-19 02:27:03.164554	2026-02-20 13:51:41.121227	\N	\N	\N
787	15722	Фреза 4-х зубая радиусная G8A47080 8*8*9*60*5070	2	1	\N	\N	2026-02-19 02:27:03.164805	2026-02-20 13:51:41.121227	\N	\N	\N
788	14597	Фреза 4-х зубая радиусная G8A47100 10*10*11*70*5070	3	1	\N	\N	2026-02-19 02:27:03.165095	2026-02-20 13:51:41.121227	\N	\N	\N
790	16294	Фреза 4-х зубая радиусная РМК22.z4.0613.57.30.R10	5	1	\N	\N	2026-02-19 02:27:03.16559	2026-02-20 13:51:41.121227	\N	\N	\N
791	15125	Фреза 4-х зубая сферическая G9634040 4*6*6*50	7	1	\N	\N	2026-02-19 02:27:03.165857	2026-02-20 13:51:41.121227	\N	\N	\N
792	15121	Фреза 4-х зубая сферическая GMG55050 5*6*13*57	7	1	\N	\N	2026-02-19 02:27:03.166101	2026-02-20 13:51:41.121227	\N	\N	\N
793	20752	Фреза 4Z*20*45	1	1	\N	\N	2026-02-19 02:27:03.166331	2026-02-20 13:51:41.121227	\N	\N	\N
794	15991	Фреза 5-ти зубая с фаской EMB72080 8*8*19*63	8	1	\N	\N	2026-02-19 02:27:03.166603	2026-02-20 13:51:41.121227	\N	\N	\N
795	16368	Фреза 5602R304GFR-1000	2	1	\N	\N	2026-02-19 02:27:03.166862	2026-02-20 13:51:41.121227	\N	\N	\N
796	15990	Фреза 6-ти зубая концевая G8D64080 8*8*36*90*5070	3	1	\N	\N	2026-02-19 02:27:03.167153	2026-02-20 13:51:41.121227	\N	\N	\N
797	22097	Фреза 6-ти зубая концевая G9I63120N 12*12*50*100 Alpha-GX	2	1	\N	\N	2026-02-19 02:27:03.167414	2026-02-20 13:51:41.121227	\N	\N	\N
798	16002	Фреза BAP300R-13-150-C12-1T	2	1	\N	\N	2026-02-19 02:27:03.167674	2026-02-20 13:51:41.121227	\N	\N	\N
799	23170	Фреза BAP300R-20-160-C20-2T	2	1	\N	\N	2026-02-19 02:27:03.16794	2026-02-20 13:51:41.121227	\N	\N	\N
800	23169	Фреза BAP300R-20-200-C20-2T	1	1	\N	\N	2026-02-19 02:27:03.168201	2026-02-20 13:51:41.121227	\N	\N	\N
801	10968	Фреза BAP400R-25-200-C25-2T	2	1	\N	\N	2026-02-19 02:27:03.168458	2026-02-20 13:51:41.121227	\N	\N	\N
802	16392	Фреза G3F08063-4C08	4	1	\N	\N	2026-02-19 02:27:03.168749	2026-02-20 13:51:41.121227	\N	\N	\N
803	15988	Фреза G4F100100-4C10	1	1	\N	\N	2026-02-19 02:27:03.16912	2026-02-20 13:51:41.121227	\N	\N	\N
804	16233	Фреза G8F08063-4C08	1	1	\N	\N	2026-02-19 02:27:03.169379	2026-02-20 13:51:41.121227	\N	\N	\N
805	23175	Фреза GE3-D10-20*60-F90 PKH105	6	1	\N	\N	2026-02-19 02:27:03.169618	2026-02-20 13:51:41.121227	\N	\N	\N
806	23165	Фреза GE3-D12 24*60 F90 PKH105	8	1	\N	\N	2026-02-19 02:27:03.169871	2026-02-20 13:51:41.121227	\N	\N	\N
807	16965	Фреза GE3-D12.0-36*75	1	1	\N	\N	2026-02-19 02:27:03.170125	2026-02-20 13:51:41.121227	\N	\N	\N
808	22095	Фреза GE4-D10.0-25*75 PK105	4	1	\N	\N	2026-02-19 02:27:03.170389	2026-02-20 13:51:41.121227	\N	\N	\N
809	22094	Фреза GE4-D10.0-40*100 PK105	3	1	\N	\N	2026-02-19 02:27:03.170646	2026-02-20 13:51:41.121227	\N	\N	\N
810	8754	Фреза GE4-D12.0-30*75 PK105	37	3	\N	\N	2026-02-19 02:27:03.170909	2026-02-20 13:51:41.121227	\N	\N	\N
811	13858	Фреза GE4-D12.0-30*75 PKH105	9	1	\N	\N	2026-02-19 02:27:03.171148	2026-02-20 13:51:41.121227	\N	\N	\N
812	8512	Фреза GE4-D12.0-30*75 PMKH205	11	1	\N	\N	2026-02-19 02:27:03.171398	2026-02-20 13:51:41.121227	\N	\N	\N
813	10701	Фреза GE4-D12.0-45*100 PK105	9	1	\N	\N	2026-02-19 02:27:03.171642	2026-02-20 13:51:41.121227	\N	\N	\N
814	22402	Фреза GE4-D12.0-60*150 PK105	2	1	\N	\N	2026-02-19 02:27:03.171886	2026-02-20 13:51:41.121227	\N	\N	\N
815	23166	Фреза GE4-D16.0-45*100 PK105	3	1	\N	\N	2026-02-19 02:27:03.172145	2026-02-20 13:51:41.121227	\N	\N	\N
816	22093	Фреза GE4-D2.0*4.0-5*50 PK105	3	1	\N	\N	2026-02-19 02:27:03.172402	2026-02-20 13:51:41.121227	\N	\N	\N
817	22092	Фреза GE4-D3.0*4.0-8*50 PK105	5	1	\N	\N	2026-02-19 02:27:03.172672	2026-02-20 13:51:41.121227	\N	\N	\N
818	18798	Фреза GE4-D8.0-20*60 PKH105	3	1	\N	\N	2026-02-19 02:27:03.172936	2026-02-20 13:51:41.121227	\N	\N	\N
819	8752	Фреза GE4R-D12.0-30*75 PKH105	17	1	\N	\N	2026-02-19 02:27:03.173199	2026-02-20 13:51:41.121227	\N	\N	\N
820	22027	Фреза GR4LX-D4.0-16*75*R1.0 PMKH205	5	1	\N	\N	2026-02-19 02:27:03.173443	2026-02-20 13:51:41.121227	\N	\N	\N
821	14603	Фреза H502F08063-6С08R02	5	1	\N	\N	2026-02-19 02:27:03.173699	2026-02-20 13:51:41.121227	\N	\N	\N
822	14760	Фреза IA21-04-11050-E4	13	1	\N	\N	2026-02-19 02:27:03.173945	2026-02-20 13:51:41.121227	\N	\N	\N
823	14759	Фреза IA21-05-13050-E4	2	1	\N	\N	2026-02-19 02:27:03.1742	2026-02-20 13:51:41.121227	\N	\N	\N
824	14608	Фреза IA21-10-25075-E4	2	1	\N	\N	2026-02-19 02:27:03.174442	2026-02-20 13:51:41.121227	\N	\N	\N
825	23167	Фреза IA30-18-45100-E4	1	1	\N	\N	2026-02-19 02:27:03.174667	2026-02-20 13:51:41.121227	\N	\N	\N
826	16244	Фреза IH26-08-40100-EL6	4	1	\N	\N	2026-02-19 02:27:03.174928	2026-02-20 13:51:41.121227	\N	\N	\N
827	8511	Фреза IH26-12-60150-EL6	1	1	\N	\N	2026-02-19 02:27:03.175184	2026-02-20 13:51:41.121227	\N	\N	\N
828	15993	Фреза IH36-12-45100-EL6	2	1	\N	\N	2026-02-19 02:27:03.175761	2026-02-20 13:51:41.121227	\N	\N	\N
829	15992	Фреза IА21-12-30075-Е6	1	1	\N	\N	2026-02-19 02:27:03.176019	2026-02-20 13:51:41.121227	\N	\N	\N
830	14602	Фреза IА21-1420-32100-R4	2	1	\N	\N	2026-02-19 02:27:03.176275	2026-02-20 13:51:41.121227	\N	\N	\N
831	15995	Фреза IА21-18-70150-ЕL4	1	1	\N	\N	2026-02-19 02:27:03.176523	2026-02-20 13:51:41.121227	\N	\N	\N
832	15989	Фреза M11F10072-4C10	2	1	\N	\N	2026-02-19 02:27:03.176785	2026-02-20 13:51:41.121227	\N	\N	\N
833	8876	Фреза PM-4EX-D12.0-G KMG405	6	1	\N	\N	2026-02-19 02:27:03.17705	2026-02-20 13:51:41.121227	\N	\N	\N
834	8873	Фреза UM-4E-D6.0-W KMG405	3	1	\N	\N	2026-02-19 02:27:03.177318	2026-02-20 13:51:41.121227	\N	\N	\N
835	8874	Фреза UM-4E-D8.0-W KMG405	2	1	\N	\N	2026-02-19 02:27:03.177579	2026-02-20 13:51:41.121227	\N	\N	\N
836	8875	Фреза UM-4EL-D10.0-W KMG405	3	1	\N	\N	2026-02-19 02:27:03.17787	2026-02-20 13:51:41.121227	\N	\N	\N
837	9860	Фреза UM-4EL-D12.0-W KMG405	5	1	\N	\N	2026-02-19 02:27:03.178169	2026-02-20 13:51:41.121227	\N	\N	\N
838	20553	Фреза дисковая 100*1,0*22	10	1	\N	\N	2026-02-19 02:27:03.178431	2026-02-20 13:51:41.121227	\N	\N	\N
839	20554	Фреза дисковая 100*2,5*22	5	1	\N	\N	2026-02-19 02:27:03.178705	2026-02-20 13:51:41.121227	\N	\N	\N
840	20555	Фреза дисковая 100*5,0*22	5	1	\N	\N	2026-02-19 02:27:03.178981	2026-02-20 13:51:41.121227	\N	\N	\N
841	20556	Фреза дисковая 160*2,0*32	5	1	\N	\N	2026-02-19 02:27:03.179257	2026-02-20 13:51:41.121227	\N	\N	\N
842	20557	Фреза дисковая 250*2,0*32	5	1	\N	\N	2026-02-19 02:27:03.179537	2026-02-20 13:51:41.121227	\N	\N	\N
843	20558	Фреза дисковая 250*5,0*32	4	1	\N	\N	2026-02-19 02:27:03.179788	2026-02-20 13:51:41.121227	\N	\N	\N
844	17418	Фреза дисковая 3х сторонняя 63*5*22, Z=16 P6M5(станок)	8	1	\N	\N	2026-02-19 02:27:03.180063	2026-02-20 13:51:41.121227	\N	\N	\N
845	20549	Фреза дисковая 80*0,5*22	10	1	\N	\N	2026-02-19 02:27:03.180337	2026-02-20 13:51:41.121227	\N	\N	\N
846	20550	Фреза дисковая 80*0,8*22	4	1	\N	\N	2026-02-19 02:27:03.180604	2026-02-20 13:51:41.121227	\N	\N	\N
847	20551	Фреза дисковая 80*1,0*22	20	2	\N	\N	2026-02-19 02:27:03.180867	2026-02-20 13:51:41.121227	\N	\N	\N
848	20552	Фреза дисковая 80*4,0*22	10	1	\N	\N	2026-02-19 02:27:03.181145	2026-02-20 13:51:41.121227	\N	\N	\N
849	7877	Фреза для снятия фасок РМК41.z4.08.XX.63.SF90	3	1	\N	\N	2026-02-19 02:27:03.181418	2026-02-20 13:51:41.121227	\N	\N	\N
850	20758	Фреза конусная алмазная 2-48мм	3	1	\N	\N	2026-02-19 02:27:03.181702	2026-02-20 13:51:41.121227	\N	\N	\N
851	7219	Фреза концевая GMJ26015 1,5*4*4*50	5	1	\N	\N	2026-02-19 02:27:03.181977	2026-02-20 13:51:41.121227	\N	\N	\N
852	13022	Фреза концевая N94.z4.10.22.72.45.F025	8	1	\N	\N	2026-02-19 02:27:03.182258	2026-02-20 13:51:41.121227	\N	\N	\N
853	7873	Фреза концевая РМК11.z4.06.13.57.30 F012	2	1	\N	\N	2026-02-19 02:27:03.182538	2026-02-20 13:51:41.121227	\N	\N	\N
854	7874	Фреза концевая РМК11.z4.08.19.63.30 F016	2	1	\N	\N	2026-02-19 02:27:03.182806	2026-02-20 13:51:41.121227	\N	\N	\N
855	7875	Фреза концевая РМК11.z4.10.22.72.30 F020	2	1	\N	\N	2026-02-19 02:27:03.183074	2026-02-20 13:51:41.121227	\N	\N	\N
856	17654	Фреза концевая РМК4.z4.12.45.100.30 F030	5	1	\N	\N	2026-02-19 02:27:03.18335	2026-02-20 13:51:41.121227	\N	\N	\N
857	14090	Фреза отрезная 80*1,6*22	9	1	\N	\N	2026-02-19 02:27:03.183623	2026-02-20 13:51:41.121227	\N	\N	\N
858	14400	Фреза пазовая сегментных шпонок 16*4,0	7	1	\N	\N	2026-02-19 02:27:03.183899	2026-02-20 13:51:41.121227	\N	\N	\N
859	20718	Фреза пазовая сегментных шпонок 19*5,0	8	1	\N	\N	2026-02-19 02:27:03.184166	2026-02-20 13:51:41.121227	\N	\N	\N
860	10731	Фреза радиусная РМК13.z4.04.11.50.30 D04	5	1	\N	\N	2026-02-19 02:27:03.184443	2026-02-20 13:51:41.121227	\N	\N	\N
861	7544	Фреза радиусная РМК22.z4.10.22.100.30 R10	3	1	\N	\N	2026-02-19 02:27:03.184727	2026-02-20 13:51:41.121227	\N	\N	\N
862	8708	Фреза радиусная РМК22.z4.12.45.100.30 R10	3	1	\N	\N	2026-02-19 02:27:03.184986	2026-02-20 13:51:41.121227	\N	\N	\N
863	8705	Фреза радиусная РМК23.z4.10.25.75.35 R10	1	1	\N	\N	2026-02-19 02:27:03.185261	2026-02-20 13:51:41.121227	\N	\N	\N
864	7876	Фреза радиусная РМК43.z4.06.XX.57.SRF08	8	1	\N	\N	2026-02-19 02:27:03.185545	2026-02-20 13:51:41.121227	\N	\N	\N
865	8608	Фреза радиусная РМК43.z4.08.XX.63.SRF10	5	1	\N	\N	2026-02-19 02:27:03.185819	2026-02-20 13:51:41.121227	\N	\N	\N
866	8609	Фреза радиусная РМК43.z4.08.XX.63.SRF15	3	1	\N	\N	2026-02-19 02:27:03.186127	2026-02-20 13:51:41.121227	\N	\N	\N
867	8768	Фреза радиусная РМК43.z4.10.XX.72.SRF25	5	1	\N	\N	2026-02-19 02:27:03.186459	2026-02-20 13:51:41.121227	\N	\N	\N
868	9139	Фреза резьбонарезная твердосплавная D3T-M12*1.75-KVX	3	1	\N	\N	2026-02-19 02:27:03.186747	2026-02-20 13:51:41.121227	\N	\N	\N
869	9143	Фреза резьбонарезная твердосплавная D3T-M16*2.0-KVX	2	1	\N	\N	2026-02-19 02:27:03.187055	2026-02-20 13:51:41.121227	\N	\N	\N
870	9135	Фреза резьбонарезная твердосплавная D3T-M6*1.0-KVX	3	1	\N	\N	2026-02-19 02:27:03.187407	2026-02-20 13:51:41.121227	\N	\N	\N
871	9137	Фреза резьбонарезная твердосплавная D3T-M8*1.25-KVX	1	1	\N	\N	2026-02-19 02:27:03.187719	2026-02-20 13:51:41.121227	\N	\N	\N
872	8508	Фреза сборная IE11-90.11Z15.016.02	1	1	\N	\N	2026-02-19 02:27:03.188039	2026-02-20 13:51:41.121227	\N	\N	\N
873	12967	Фреза сборная IF22-45.12C40.160.08	2	1	\N	\N	2026-02-19 02:27:03.18832	2026-02-20 13:51:41.121227	\N	\N	\N
874	7753	Фреза твердосплавная MPMHVRBD1000R300	2	1	\N	\N	2026-02-19 02:27:03.188726	2026-02-20 13:51:41.121227	\N	\N	\N
875	16255	Фреза торцевая PE01.11А22.050.06	8	1	\N	\N	2026-02-19 02:27:03.189038	2026-02-20 13:51:41.121227	\N	\N	\N
876	12636	Фреза торцевая PE01.16B40.125.10 (EMP02-125-B40-AP16-10)	1	1	\N	\N	2026-02-19 02:27:03.189411	2026-02-20 13:51:41.121227	\N	\N	\N
877	22792	Фреза трехсторонняя с рифлеными ножами D300*12*50 z30	4	1	\N	\N	2026-02-19 02:27:03.189723	2026-02-20 13:51:41.121227	\N	\N	\N
878	19791	Цанга ER32 13*0,015мм	5	1	\N	\N	2026-02-19 02:27:03.189998	2026-02-20 13:51:41.121227	\N	\N	\N
879	20403	Цанга ER32 14*0,015	5	1	\N	\N	2026-02-19 02:27:03.190298	2026-02-20 13:51:41.121227	\N	\N	\N
880	19792	Цанга ER32 15*0,015мм	5	1	\N	\N	2026-02-19 02:27:03.19058	2026-02-20 13:51:41.121227	\N	\N	\N
881	20404	Цанга ER32 16*0,015	3	1	\N	\N	2026-02-19 02:27:03.190851	2026-02-20 13:51:41.121227	\N	\N	\N
882	19793	Цанга ER32 17*0,015мм	4	1	\N	\N	2026-02-19 02:27:03.19113	2026-02-20 13:51:41.121227	\N	\N	\N
883	20405	Цанга ER32 18*0,015	3	1	\N	\N	2026-02-19 02:27:03.191409	2026-02-20 13:51:41.121227	\N	\N	\N
884	19794	Цанга ER32 20*0,015мм	3	1	\N	\N	2026-02-19 02:27:03.191711	2026-02-20 13:51:41.121227	\N	\N	\N
682	15134	Цанга ER32G-12,5*10	8	1	\N	\N	2026-02-19 02:27:03.135613	2026-02-20 13:51:41.121227	\N	\N	\N
885	8774	Цанга быстросменная резьбонарезная GT12-ISO М10 8*6.3	1	1	\N	\N	2026-02-19 02:27:03.192346	2026-02-20 13:51:41.121227	\N	\N	\N
886	8775	Цанга быстросменная резьбонарезная GT12-ISO-5*4	2	1	\N	\N	2026-02-19 02:27:03.192638	2026-02-20 13:51:41.121227	\N	\N	\N
887	8778	Цанга быстросменная резьбонарезная GT12-ISO-6,3*5	1	1	\N	\N	2026-02-19 02:27:03.192885	2026-02-20 13:51:41.121227	\N	\N	\N
888	8777	Цанга быстросменная резьбонарезная GT12-ISO-9*7,1	3	1	\N	\N	2026-02-19 02:27:03.193169	2026-02-20 13:51:41.121227	\N	\N	\N
889	8776	Цанга быстросменная резьбонарезная GT12-JIS-5.5*4.5	2	1	\N	\N	2026-02-19 02:27:03.193455	2026-02-20 13:51:41.121227	\N	\N	\N
890	8779	Цанга быстросменная резьбонарезная GT12-JIS-6*4,5	3	1	\N	\N	2026-02-19 02:27:03.193748	2026-02-20 13:51:41.121227	\N	\N	\N
891	10227	Цанга быстросменная резьбонарезная ISO-GT12 M14 11.2*9	3	1	\N	\N	2026-02-19 02:27:03.194052	2026-02-20 13:51:41.121227	\N	\N	\N
892	13870	Цанга быстросменная резьбонарезная ISO-GT24 М22 16*12,5	2	1	\N	\N	2026-02-19 02:27:03.194349	2026-02-20 13:51:41.121227	\N	\N	\N
893	1246	Цанга высокоточная ER32-25 AA	5	1	\N	\N	2026-02-19 02:27:03.194627	2026-02-20 13:51:41.121227	\N	\N	\N
\.


--
-- Data for Name: material_instances; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.material_instances (id, app_id, mark_id, mark_name, mark_gost, sortament_id, sortament_name, sortament_gost, dimension1, dimension2, dimension3, price_per_ton, price_per_piece, created_by, created_at, lotzman_id, volume_argument, volume_value, price_per_kg, type_size, dimensions) FROM stdin;
1	b3ebfbb1	5d60617b	АК7ч	\N	c4fe4069	Фасонная заготовка	\N	209	842	606	\N	80000	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
2	682f308d	5d60617b	АК7ч	\N	c4fe4069	Фасонная заготовка	\N	180	842	606	\N	86400	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
3	0c6da4b0	5d60617b	Сплав АК7ч	ГОСТ 1583 - 93	c4fe4069	Фасонная заготовка	\N	44	159	110	\N	1100	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
4	d920fb39	5d60617b	АК7ч	\N	c4fe4069	Фасонная заготовка	\N	18	125	110	\N	450	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
5	57e241cd	5d60617b	АК7ч	\N	c4fe4069	Фасонная заготовка	\N	43	143	110	\N	950	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
6	add61c9b	f654fde7	Алюминий АД1Н	\N	6b1bbecc	Лист	\N	32	\N	\N	500000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
7	6db8e84c	f654fde7	Алюминий АД1Н	\N	74ea7c28	Круг	\N	18	\N	\N	500000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
9	501c991e	514227aa	Алюминий АМг3	\N	6b1bbecc	Лист	\N	30	\N	\N	443000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
10	2a2c8b89	514227aa	Алюминий АМг3	\N	6b1bbecc	Лист	\N	35	\N	\N	443000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
11	6315b3fc	640dbed2	Алюминий АМг6	\N	6b1bbecc	Лист	\N	3	\N	\N	595000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
12	faeb50da	6eb58e25	Алюминий Д16	\N	6b1bbecc	Лист	\N	20	\N	\N	439000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
13	9bdc81e9	6eb58e25	Алюминий Д16	\N	6b1bbecc	Лист	\N	45	\N	\N	439000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
14	c222a98c	ba8ec2dc	Алюминий Д16Т	\N	6b1bbecc	Лист	\N	20	\N	\N	605000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
15	f5aff9a9	ba8ec2dc	Алюминий Д16Т	\N	6b1bbecc	Лист	\N	50	\N	\N	786000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
16	4b83bf75	474d0132	Сталь 09Г2С	\N	6b1bbecc	Лист	\N	6	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
17	59122102	cf1d0a01	Сталь 12Х2Н4А	\N	74ea7c28	Круг	\N	140	\N	\N	215800	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
18	b835f881	9dcb1c27	Сталь 12ХН3А	\N	74ea7c28	Круг	\N	140	\N	\N	215800	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
19	c47db323	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	10	\N	\N	67000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
20	5745e7c9	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	75	\N	\N	77700	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
21	f0bee902	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	20	\N	\N	86000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
22	eb7d6b70	dfa806d2	Сталь 20	\N	28593e67	Поковка круглая	\N	500	300	\N	\N	114600	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
23	095390c1	e1ded7ce	Сталь 20ХН3А	\N	74ea7c28	Круг	\N	20	\N	\N	180000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
24	491fc178	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	500	\N	\N	177000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
26	1c6c9375	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	14	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
27	1caf3b70	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	3	\N	\N	66000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
28	a6793e1a	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	75	\N	\N	110000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
29	70941d41	8170dab6	Сталь 3	\N	28593e67	Поковка круглая	\N	500	300	\N	\N	114600	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
30	f11fdb86	5f55e0df	Сталь 38ХС	\N	74ea7c28	Круг	\N	25	\N	\N	96000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
31	e3592289	26fd6289	Сталь 40	\N	74ea7c28	Круг	\N	55	\N	\N	60000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
32	c8b7ceba	5bbb205f	Сталь 40-Б	\N	74ea7c28	Круг	\N	10	\N	\N	135000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
33	baa9bac9	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	100	\N	\N	74000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
34	1b43d78f	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	155	\N	\N	81666.66666666667	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
35	133fdfe4	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	18	\N	\N	90000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
36	dcfdf696	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	20	\N	\N	90000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
37	5e902312	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	200	\N	\N	95000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
40	cf98f1b2	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	65	\N	\N	74000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
41	b8f4d8a1	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	60	\N	\N	159609	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
42	09da31be	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	45	\N	\N	140000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
43	6b443db0	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	50	\N	\N	140000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
44	04ce6799	1f4f991a	Сталь 40Х	\N	28593e67	Поковка круглая	\N	550	220	\N	220000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
45	79246cd6	1f4f991a	Сталь 40Х	\N	28593e67	Поковка круглая	\N	650	220	\N	\N	113333	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
46	573b08e3	f3b25c46	Сталь 45	\N	74ea7c28	Круг	\N	22	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
47	a642202e	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	18	\N	\N	100000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
48	84fc3176	f7398bdd	Сталь 65Г	\N	6b1bbecc	Лист	\N	3	\N	\N	200000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
49	a7bf19db	f7398bdd	Сталь 65Г	\N	6b1bbecc	Лист	\N	4	\N	\N	150000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
50	2b958dd1	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	10	\N	\N	66000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
51	86270ce5	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	12	\N	\N	66000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
25	f0d4d0a7	8170dab6	Сталь 3	\N	6b1bbecc	Лист	\N	1	\N	\N	66000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
38	71e99cb9	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	330	\N	\N	140833.3333333333	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
52	4e3c2c8d	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	40	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
53	3937eae2	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	16	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
54	f393c25c	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	25	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
55	e0a5bf61	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	40	\N	\N	77700	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
56	d1fe2111	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	60	\N	\N	74000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
57	44e07466	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	25	\N	\N	82800	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
58	f003e965	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	30	\N	\N	82800	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
59	8a642ec4	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	45	\N	\N	77700	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
60	4149b4f0	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	80	\N	\N	74000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
61	8f831c89	4300e873	Сталь 40ХН	\N	74ea7c28	Круг	\N	16	\N	\N	130000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
62	45f544b9	f3b25c46	Сталь 45	\N	74ea7c28	Круг	\N	65	\N	\N	75900	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
63	c221df0f	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	20	\N	\N	82000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
64	2e9a707f	7fde857e	Алюминий АМг5	\N	74ea7c28	Круг	\N	40	\N	\N	1300000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
65	36cdf43a	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	40	\N	\N	77000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
66	a9ffe08f	ba8ec2dc	Алюминий Д16Т	\N	74ea7c28	Круг	\N	40	\N	\N	1100000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
67	ef27c009	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	22	\N	\N	88350	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
68	3887d3a1	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	8	\N	\N	76400	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
69	f1101ede	f7398bdd	Сталь 65Г	\N	6b1bbecc	Лист	\N	2	\N	\N	161350	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
70	1b09722f	c7fc5394	Сталь 30ХГСА	\N	74ea7c28	Круг	\N	200	\N	\N	95000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
71	9ca39f3c	21ee9690	Сталь 30ХГТ	\N	74ea7c28	Круг	\N	65	\N	\N	79000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
72	e4ab7a6d	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	22	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
73	830bcb87	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	12	\N	\N	77000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
74	99194147	21ee9690	Сталь 30ХГТ	\N	74ea7c28	Круг	\N	55	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
75	6dd126fd	21ee9690	Сталь 30ХГТ	\N	74ea7c28	Круг	\N	110	\N	\N	79000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
76	8e7750d0	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	260	\N	\N	122000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
77	c3debd13	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	4	\N	\N	72000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
78	050d26d2	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	30	\N	\N	119000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
79	a11270ba	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	85	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
80	51edd7b7	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	140	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
81	c5436335	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	16	\N	\N	71000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
82	5e419887	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	30	\N	\N	85000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
83	9a5a23c5	dfa806d2	Сталь 20	\N	6b1bbecc	Лист	\N	12	\N	\N	73000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
84	266e788a	6eb58e25	Алюминий Д16	\N	6b1bbecc	Лист	\N	15	\N	\N	415000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
85	7cac8145	282dc277	ТМКЩ-М-5	\N	6b1bbecc	Лист	\N	5	\N	\N	950000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
86	637ec60f	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	102	10	\N	140000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
87	d7892752	c7fc5394	Сталь 30ХГСА	\N	74ea7c28	Круг	\N	210	\N	\N	95000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
88	f207eba0	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	140	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
89	97fd6985	f3b25c46	Сталь 45	\N	74ea7c28	Круг	\N	25	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
90	34bcc451	c98548b6	Сталь 35	\N	a3df9c38	Шестигранник	\N	24	\N	\N	90000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
91	a3a1e1e9	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	18	\N	\N	115000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
92	3a02ab01	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	100	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
93	fee0c361	474d0132	Сталь 09Г2С	\N	6b1bbecc	Лист	\N	5	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
95	d7f309a1	c98548b6	Сталь 35	ГОСТ 1050-88	74ea7c28	Круг	ГОСТ 2590-88	25	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
96	39957767	a6a075e2	Полиэтилен НД	\N	6b1bbecc	Лист	\N	6	\N	\N	330000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
97	dfffe424	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	114	16	\N	150000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
98	8855826c	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	146	6	\N	150000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
100	93f5ecdf	ba8ec2dc	Алюминий Д16Т	\N	b9d2585c	Плита	\N	30	\N	\N	786000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
101	0f9cb935	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	110	\N	\N	76000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
102	a2605b95	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	85	\N	\N	77000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
103	240cdf5c	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	20	\N	\N	110000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
157	bd0dbe1e	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	42	\N	\N	80000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
104	8b372713	1f4f991a	Сталь 40Х	\N	a4bd5798	Труба круглая	\N	270	40	\N	600000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
105	eb503e23	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	270	\N	\N	122000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
106	c1d6012b	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	240	\N	\N	110000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
107	ef63bfb6	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	10	\N	\N	130000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
108	a1a8768f	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	210	\N	\N	81000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
109	ecef876b	6415066c	Сталь 18ХГТ	\N	74ea7c28	Круг	\N	200	\N	\N	92500	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
110	99efd277	6415066c	Сталь 18ХГТ	\N	74ea7c28	Круг	\N	165	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
111	43ca0338	6415066c	Сталь 18ХГТ	\N	74ea7c28	Круг	\N	115	\N	\N	74000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
112	cfa623f0	190a8599	Сталь 10	\N	6b1bbecc	Лист	\N	6	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
113	94d9593e	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	3	\N	\N	140000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
114	62c46eee	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	170	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
115	5b32d86e	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	16	\N	\N	115000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
116	040e4583	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	150	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
117	5a2e5089	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	30	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
118	c1e554b4	28245fae	10ХСНД	\N	6b1bbecc	Лист	\N	16	\N	\N	125000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
119	051d718c	190a8599	Сталь 10	\N	74ea7c28	Круг	\N	120	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
120	79cba33f	28245fae	10ХСНД	\N	6b1bbecc	Лист	\N	8	\N	\N	125000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
121	ddb59cbe	28245fae	10ХСНД	\N	6b1bbecc	Лист	\N	22	\N	\N	135000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
122	c9638a8a	6415066c	Сталь 18ХГТ	\N	74ea7c28	Круг	\N	210	\N	\N	90000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
123	1e3cc46f	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	160	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
124	8928aac6	f20cebd5	Сталь ШХ15	\N	74ea7c28	Круг	\N	250	\N	\N	223000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
125	b27045fe	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	89	5	\N	170000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
126	2d0d5ecc	16df45aa	38ХН3МФА	\N	74ea7c28	Круг	\N	35	\N	\N	378000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
127	8026da14	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	130	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
128	ffdc75fa	16df45aa	38ХН3МФА	\N	74ea7c28	Круг	\N	50	\N	\N	370000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
129	ad1d0710	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	25	\N	\N	110000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
131	ec6db173	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	120	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
132	b703dc23	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	105	\N	\N	70000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
134	2ca156c0	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	90	\N	\N	76000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
135	c0c3ad83	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	80	\N	\N	76000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
136	127899f5	26fd6289	Сталь 40	\N	a3df9c38	Шестигранник	\N	19	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
137	a7f73cb7	26fd6289	Сталь 40	\N	a3df9c38	Шестигранник	\N	22	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
138	ea4cf777	5f55e0df	Сталь 38ХС	\N	74ea7c28	Круг	\N	14	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
139	940d9821	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	36	\N	\N	99000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
140	5138832b	1f4f991a	Сталь 40Х	\N	b35b566c	Квадрат	\N	25	\N	\N	100000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
141	e9091f41	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	40	\N	\N	98000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
142	3312fd78	1f4f991a	Сталь 40Х	\N	6b1bbecc	Лист	\N	32	\N	\N	75000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
143	0e7a76c8	f3b25c46	Сталь 45	\N	74ea7c28	Круг	\N	190	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
144	8ef362c0	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	50	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
145	0d070c06	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	24	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
146	a87fbc04	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	36	\N	\N	80000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
147	37dc9f37	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	17	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
148	9b7bdbae	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	57	4	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
149	e45e9ecc	8170dab6	Сталь 3	\N	a4bd5798	Труба круглая	\N	38	2	\N	80000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
150	67e2a18c	dfa806d2	Сталь 20	\N	a4bd5798	Труба круглая	\N	45	4	\N	101667	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
151	72f88a9f	f3b25c46	Сталь 45	\N	6b1bbecc	Лист	\N	13	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
152	65457b2c	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	35	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
153	8279063b	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	25	\N	\N	80000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
154	b013e083	474d0132	Сталь 09Г2С	\N	74ea7c28	Круг	\N	20	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
155	bcaf9d57	dfa806d2	Сталь 20	\N	74ea7c28	Круг	\N	32	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
156	edfa5bbb	474d0132	Сталь 09Г2С	\N	6b1bbecc	Лист	\N	16	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
158	c511de77	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	130	\N	\N	80000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
159	d243f872	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	36	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
160	603f43f5	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	16	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
161	16af4287	1f4f991a	Сталь 40Х	\N	a4bd5798	Труба круглая	\N	45	7	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
162	bf5db592	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	70	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
163	deff1d47	812e16c3	Сталь 12Х18Н10Т	\N	74ea7c28	Круг	\N	42	\N	\N	360000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
164	9b81ac5f	dfa806d2	Сталь 20	\N	b35b566c	Квадрат	\N	24	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
165	b4e49827	812e16c3	Сталь 12Х18Н10Т	\N	a4bd5798	Труба круглая	\N	42	9	\N	360000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
166	4b577dea	474d0132	Сталь 09Г2С	\N	6b1bbecc	Лист	\N	10	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
167	3732d5fe	c7fc5394	Сталь 30ХГСА	\N	a4bd5798	Труба круглая	\N	89	12	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
168	a2e3aa98	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	12	\N	\N	80000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
169	50c658a4	474d0132	Сталь 09Г2С	\N	6b1bbecc	Лист	\N	25	\N	\N	\N	\N	o.pushkova@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
170	7937be5b	8170dab6	Сталь 3	\N	74ea7c28	Круг	\N	14	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
171	f232c621	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	19	\N	\N	\N	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
172	a1af95d9	c7fc5394	Сталь 30ХГСА	\N	6b1bbecc	Лист	\N	8	\N	\N	63334	\N	o.pushkova@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
173	728168a2	f3b25c46	Сталь 45	\N	a3df9c38	Шестигранник	\N	27	\N	\N	20000	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
174	5567d625	f3b25c46	Сталь 45	\N	6b1bbecc	Лист	\N	5	\N	\N	32355	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
175	04bc54fe	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	12	\N	\N	78217	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
176	6a401b08	c98548b6	Сталь 35	\N	74ea7c28	Круг	\N	60	\N	\N	75000	\N	o.pushkova@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
177	a220f409	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	75	\N	\N	78217	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
178	438c38c6	1f4f991a	Сталь 40Х	\N	74ea7c28	Круг	\N	190	\N	\N	78217	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
179	11553685	c7fc5394	Сталь 30ХГСА	\N	a4bd5798	Труба круглая	\N	68	3	\N	63334	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
181	14f54f50	812e16c3	Сталь 12Х18Н10Т	\N	74ea7c28	Круг	\N	50	\N	\N	360000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
8	708f2a43	d2c4a8fe	Алюминий АМг2М	\N	a4bd5798	Труба круглая	\N	6	1	\N	1152000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
180	175e886a	b7e072d8	Алюминий АД1М	\N	74ea7c28	Круг	\N	20	\N	\N	0	\N	a.neminushii@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
182	MAT_1775615649	\N	Сталь 45	\N	\N	Круг	\N	40	\N	\N	\N	\N	Пушкова Оксана	2026-04-08 10:34:09.657391	\N	\N	\N	\N	\N	\N
185	MAT_1775616615	\N	Сталь 40	\N	\N	Шестигранник	\N	32	\N	\N	\N	\N	Пушкова Оксана	2026-04-08 10:50:15.787776	\N	\N	\N	\N	\N	\N
186	MAT_1775616616	\N	Сталь 40	\N	\N	Шестигранник	\N	32	\N	\N	\N	\N	Пушкова Оксана	2026-04-08 10:50:16.520264	\N	\N	\N	\N	\N	\N
99	fc9c05d3	a81964bd	Капролон	ГОСТ 7850-86	74ea7c28	Круг	\N	25	\N	\N	1040000	\N	a.krasnoshtanov@izgtgroup.ru	2026-02-20 21:07:36.101339	\N	\N	\N	\N	\N	\N
189	MAT_1776919946	\N	Сталь 3	\N	\N	Круг	\N	100	\N	\N	\N	\N	Пушкова Оксана	2026-04-23 12:52:26.8224	\N	\N	\N	\N	\N	\N
190	MAT_1776929554	\N	Сталь 40Х	\N	\N	Круг	\N	50	\N	\N	\N	\N	Пушкова Оксана	2026-04-23 15:32:34.823037	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: materials; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.materials (id, name, description, unit, is_active, created_at, updated_at, app_id, lotzman_id, density) FROM stdin;
13	Сплав АК7ч	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
14	Алюминий Д16	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
15	Алюминий АД1М	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
16	Алюминий АД1Н	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
17	Алюминий АМг2М	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
18	Алюминий АМг6	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
19	Алюминий АМг3	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
20	БрАЖ9-4	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
21	Д16АМ-1	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
22	Картон	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
23	Сталь 10	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
24	Сталь 12Х2Н4А	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
25	Сталь 12ХН3А	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
26	Сталь 20	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
27	Сталь 3	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
28	Сталь 40Х	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
29	Сталь 45Х	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
30	Сталь ШХ15	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
31	Фторопласт	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
32	Чугун	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
33	Сталь 30ХГТ	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
34	Сталь 30ХГСА	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
35	Сталь 38ХС	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
36	Сталь 40	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
37	Сталь 20ХН3А	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
38	Алюминий Д16Т	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
39	Сталь 45	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
40	Сталь 09Г2С	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
41	Сталь 65Г	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
42	Сталь 40-Б	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
43	Сталь 40ХН	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
44	Алюминий АМг5	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
45	Алюминий АМг5М	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
46	ТМКЩ-М-5	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
47	Сталь 35	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
48	Полиэтилен НД	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
49	Капролон	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
50	Сталь 18ХГТ	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
51	Сталь 10ХСНД	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
52	Сталь 38ХГМФТ	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
53	Сталь 38ХН3МФА	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
54	Сталь 12Х18Н10Т	\N	кг	t	2026-02-20 21:01:51.559769	2026-02-20 21:01:51.559769	\N	\N	\N
\.


--
-- Data for Name: operation_cooperative; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.operation_cooperative (id, operation_type_id, cooperative_id) FROM stdin;
1	21	1
2	30	1
3	31	1
4	35	1
5	36	1
6	38	1
7	21	2
8	30	2
9	31	2
10	35	2
11	36	2
12	21	3
13	30	3
14	31	3
15	35	3
16	36	3
\.


--
-- Data for Name: operation_equipment; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.operation_equipment (id, operation_type_id, equipment_id) FROM stdin;
31	12	2
32	12	3
33	14	4
34	14	5
35	14	6
36	15	8
37	20	23
39	22	12
40	22	13
41	22	14
42	22	24
43	22	25
47	22	27
48	24	16
49	24	17
50	24	28
53	24	30
54	26	31
56	17	33
57	10	1
58	11	20
59	11	21
60	13	19
61	16	7
62	19	9
63	21	10
64	21	34
65	29	22
66	30	10
67	30	34
68	31	10
69	31	34
71	33	12
72	33	13
73	33	14
74	35	10
75	35	34
76	36	10
77	36	34
78	39	36
79	37	32
80	25	18
81	25	35
83	18	42
84	24	51
85	24	52
86	22	48
87	22	49
88	22	50
89	22	53
90	33	53
91	22	54
92	33	54
93	22	55
94	33	55
95	22	56
96	33	56
97	22	57
98	33	57
\.


--
-- Data for Name: operation_types; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.operation_types (id, name, description, default_duration, is_active, created_at, updated_at) FROM stdin;
10	вальцовочная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
11	листогибочная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
12	зубодолбежная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
13	резка лазерная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
14	зуборезная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
15	резьбонарезная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
16	отрезная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
17	очистка пескоструйная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
18	сборочная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
19	сварочная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
20	сверлильная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
21	отжиг	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
22	токарная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
23	транспортирование	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
24	фрезерная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
26	электроэрозионная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
27	расточная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
28	литейная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
29	резка плазменная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
30	улучшение	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
31	закалка	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
32	ленточно-шлифовальная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
33	обдирочная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
34	заточная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
35	отпуск высокий	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
36	отпуск	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
37	плоскошлифовальная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
38	галтовка	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
39	слесарная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
25	кругошлифовальная	\N	60	t	2026-02-20 21:01:51.576807	2026-02-20 21:01:51.576807
\.


--
-- Data for Name: operation_workshop; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.operation_workshop (id, operation_type_id, workshop_id) FROM stdin;
1	12	6
2	14	6
3	15	6
4	20	6
5	22	6
6	24	6
7	26	6
8	37	6
9	17	7
10	10	8
11	11	8
12	13	8
13	16	8
14	18	8
15	19	8
16	21	8
17	23	8
18	27	8
19	29	8
20	30	8
21	31	8
22	33	8
23	34	8
24	35	8
25	36	8
26	38	8
27	39	8
28	25	6
\.


--
-- Data for Name: order_priorities; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.order_priorities (id, order_id, priority, deadline, notes, created_at, updated_at) FROM stdin;
104	84	5	\N	\N	\N	\N
165	88	5	\N	\N	\N	\N
166	89	5	\N	\N	\N	\N
167	90	5	\N	\N	\N	\N
31	70	5	\N	\N	\N	\N
32	69	5	\N	\N	\N	\N
101	82	5	\N	\N	\N	\N
102	83	5	\N	\N	\N	\N
\.


--
-- Data for Name: order_schedule; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.order_schedule (id, order_id, equipment_name, operation_name, schedule_date, parts, created_at) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.orders (id, route_id, quantity, blanks_needed, route_quantity, pdf_path, created_by, created_at, start_date, end_date, app_id, id_1c, order_number, lot_size, file, status, in_progress, blanks_quantity, blank_size, preprocessing_size, updated_at, production_type, batch_number, manual_detail_name, manual_quantity, designation, detail_name, mark_name, sortament_name, route_card_data) FROM stdin;
82	93	30	30	1	\N	admin	2026-04-16 08:50:29.138756	\N	\N	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш009	\N	\N	CK-6.01.001	Труба	\N	\N	\N
83	94	40	40	1	\N	admin	2026-04-16 08:50:40.145587	\N	\N	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш010	\N	\N	CK-6.01.001	Труба	\N	\N	{"history": [], "operations": [{"comment": "", "defects": 0, "operators": [{"id": 7, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 13, "operation_id": 378, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": "Токарный 1М63МФ101", "operation_date": "", "operation_name": "токарная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 1}, {"comment": "", "defects": 0, "operators": [], "equipment_id": null, "operation_id": 379, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": null, "operation_date": "", "operation_name": "закалка", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 2}, {"comment": "", "defects": 0, "operators": [{"id": 7, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 30, "operation_id": 380, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": "Фрезерный KVL1361", "operation_date": "", "operation_name": "фрезерная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 3}]}
69	92	40	40	1	\N	admin	2026-04-12 10:48:58.407158	24.04.2026	19.05.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	2026-04-21 08:31:21.495242	piece	Ш001	\N	\N	L101.10.05.601	Фланец проходной 8.10.708	\N	\N	{"history": [], "operations": [{"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 52, "operation_id": 370, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": "Фрезерный IMU-5x400_№2", "operation_date": "2026-05-04", "operation_name": "фрезерная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 1}, {"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 53, "operation_id": 369, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": "Токарный 16К20_(1)", "operation_date": "2026-05-12", "operation_name": "токарная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 2}, {"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 48, "operation_id": 368, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 40, "workshop_name": "", "equipment_name": "Токарный NL2500_№1", "operation_date": "2026-05-20", "operation_name": "токарная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 3}]}
87	100	10	10	1	\N	Пушкова Оксана	2026-04-23 13:09:50.63617	\N	\N	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш014	\N	\N	PO.BMEX.404.200.009	Кольцо	\N	\N	\N
88	101	12	2	10	\N	Пушкова Оксана	2026-04-23 13:45:26.557565	23.04.2026	11.05.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш015	\N	\N	8.10.233	Кольцо стопорное	\N	\N	\N
70	92	20	20	1	\N	admin	2026-04-12 10:49:38.524746	24.04.2026	06.05.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш002	\N	\N	L101.10.05.601	Фланец проходной 8.10.708	\N	\N	\N
89	101	20	2	10	\N	Пушкова Оксана	2026-04-23 15:37:45.971202	23.04.2026	27.05.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш016	\N	\N	8.10.233	Кольцо стопорное	\N	\N	\N
90	100	5	5	1	\N	admin	2026-04-23 15:39:55.750928	23.04.2026	24.04.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш017	\N	\N	PO.BMEX.404.200.009	Кольцо	\N	\N	\N
84	95	50	50	1	\N	admin	2026-04-16 08:50:51.538419	21.04.2026	04.06.2026	\N	\N	\N	\N	\N	новый	f	\N	\N	\N	\N	piece	Ш011	\N	\N	CK-6.01.001	Труба	\N	\N	{"history": [{"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:08.644283Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "True", "timestamp": "2026-04-22T00:13:22.592639Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "False", "old_value": "True", "timestamp": "2026-04-22T00:13:24.065538Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:26.584845Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "False", "old_value": "True", "timestamp": "2026-04-22T00:13:28.170840Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:30.098218Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:32.220837Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:34.465032Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:13:39.742282Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:15.400840Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:19.515757Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:21.303808Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:23.727147Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:25.910134Z"}, {"field": "otk_approved", "user_id": 11, "username": "Александр", "new_value": "True", "old_value": "False", "timestamp": "2026-04-22T00:15:36.354390Z"}], "operations": [{"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 13, "operation_id": 382, "operator_fio": "", "otk_approved": true, "quantity_fact": 0, "quantity_plan": 50, "workshop_name": "", "equipment_name": "Токарный 1М63МФ101", "operation_date": "2026-05-01", "operation_name": "токарная", "otk_approved_at": "2026-04-22T00:15:19.515733", "otk_approved_by": 11, "sequence_number": 1}, {"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 30, "operation_id": 383, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 50, "workshop_name": "", "equipment_name": "Фрезерный KVL1361", "operation_date": "2026-05-13", "operation_name": "фрезерная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 2}, {"comment": "", "defects": 0, "operators": [], "equipment_id": null, "operation_id": 381, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 50, "workshop_name": "", "equipment_name": null, "operation_date": "2026-05-13", "operation_name": "закалка", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 3}, {"comment": "", "defects": 0, "operators": [{"id": 21, "username": "Братушкин Роман", "fio_short": "Братушкин Р."}], "equipment_id": 35, "operation_id": 389, "operator_fio": "", "otk_approved": false, "quantity_fact": 0, "quantity_plan": 50, "workshop_name": "", "equipment_name": "Круглошлифовальный 3М151В", "operation_date": "2026-06-01", "operation_name": "кругошлифовальная", "otk_approved_at": null, "otk_approved_by": null, "sequence_number": 4}]}
\.


--
-- Data for Name: planning_rules; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.planning_rules (id, key, value, created_at) FROM stdin;
1	allow_manual_entry	false	2026-04-15 13:16:43.571788
\.


--
-- Data for Name: production_schedule; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.production_schedule (id, order_id, route_operation_id, equipment_id, planned_date, actual_date, status, priority, quantity, duration_minutes, notes, is_manual_override, created_at, updated_at, taken_at, completed_at, taken_by, completed_by, is_cooperation, coop_company_name, coop_duration_days) FROM stdin;
4361	89	408	19	2026-04-23 00:00:00	\N	planned	5	20	2	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4362	89	409	34	2026-05-04 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4363	89	409	34	2026-05-05 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4364	89	409	34	2026-05-06 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4365	89	410	34	2026-05-07 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4366	89	410	34	2026-05-08 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4367	89	410	34	2026-05-11 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4368	89	411	34	2026-05-12 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4369	89	411	34	2026-05-13 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4370	89	411	34	2026-05-14 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4371	89	412	33	2026-05-15 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4372	89	412	33	2026-05-18 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4391	69	370	52	2026-04-24 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4392	69	370	52	2026-04-27 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4393	69	370	52	2026-04-28 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4394	69	370	52	2026-04-29 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4395	69	370	52	2026-04-30 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4396	69	370	52	2026-05-01 00:00:00	\N	planned	5	5	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4397	69	369	53	2026-05-04 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4398	69	369	53	2026-05-05 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4399	69	369	53	2026-05-06 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4400	69	369	53	2026-05-07 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4401	69	369	53	2026-05-08 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4402	69	369	53	2026-05-11 00:00:00	\N	planned	5	5	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4373	89	412	33	2026-05-19 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4307	84	382	13	2026-04-23 00:00:00	\N	in_progress	5	7	25	\N	\N	\N	\N	2026-04-23 12:25:23.772068	\N	Пушкова Оксана	\N	f	\N	\N
4348	88	408	19	2026-04-23 00:00:00	\N	planned	5	12	2	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4349	88	409	34	2026-04-24 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4350	88	409	34	2026-04-27 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4351	88	410	34	2026-04-28 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4352	88	410	34	2026-04-29 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4353	88	411	34	2026-04-30 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4354	88	411	34	2026-05-01 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4355	88	412	33	2026-05-04 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4356	88	412	33	2026-05-05 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4357	88	413	32	2026-05-06 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4358	88	413	32	2026-05-07 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4359	88	414	36	2026-05-08 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4360	88	414	36	2026-05-11 00:00:00	\N	planned	5	5	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4374	89	413	32	2026-05-20 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4305	84	382	13	2026-04-21 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4306	84	382	13	2026-04-22 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4308	84	382	13	2026-04-24 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4309	84	382	13	2026-04-27 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4310	84	382	13	2026-04-28 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4311	84	382	13	2026-04-29 00:00:00	\N	planned	5	7	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4375	89	413	32	2026-05-21 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4376	89	413	32	2026-05-22 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4377	89	414	36	2026-05-25 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4378	89	414	36	2026-05-26 00:00:00	\N	planned	5	7	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4379	89	414	36	2026-05-27 00:00:00	\N	planned	5	6	60	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4380	90	406	7	2026-04-23 00:00:00	\N	planned	5	5	2	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4312	84	382	13	2026-04-30 00:00:00	\N	planned	5	1	25	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4313	84	383	30	2026-05-01 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4314	84	383	30	2026-05-04 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4315	84	383	30	2026-05-05 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4316	84	383	30	2026-05-06 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4317	84	383	30	2026-05-07 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4318	84	383	30	2026-05-08 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4319	84	383	30	2026-05-11 00:00:00	\N	planned	5	7	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4381	90	407	50	2026-04-24 00:00:00	\N	planned	5	5	3	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4382	70	370	51	2026-04-24 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4383	70	370	51	2026-04-27 00:00:00	\N	planned	5	7	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4384	70	370	51	2026-04-28 00:00:00	\N	planned	5	6	55	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4385	70	369	53	2026-04-29 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4386	70	369	53	2026-04-30 00:00:00	\N	planned	5	7	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4387	70	369	53	2026-05-01 00:00:00	\N	planned	5	6	40	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4388	70	368	48	2026-05-04 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4389	70	368	48	2026-05-05 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4390	70	368	48	2026-05-06 00:00:00	\N	planned	5	6	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4320	84	383	30	2026-05-12 00:00:00	\N	planned	5	1	15	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4321	84	381	\N	2026-05-13 00:00:00	\N	planned	5	50	\N	\N	\N	\N	\N	\N	\N	\N	\N	t	Оргтехоснастка	6
4322	84	389	35	2026-05-20 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4323	84	389	35	2026-05-21 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4324	84	389	35	2026-05-22 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4325	84	389	35	2026-05-25 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4326	84	389	35	2026-05-26 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4327	84	389	35	2026-05-27 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4328	84	389	35	2026-05-28 00:00:00	\N	planned	5	7	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4329	84	389	35	2026-05-29 00:00:00	\N	planned	5	1	250	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4403	69	368	48	2026-05-12 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4404	69	368	48	2026-05-13 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4405	69	368	48	2026-05-14 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4406	69	368	48	2026-05-15 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4407	69	368	48	2026-05-18 00:00:00	\N	planned	5	7	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
4408	69	368	48	2026-05-19 00:00:00	\N	planned	5	5	30	\N	\N	\N	\N	\N	\N	\N	\N	f	\N	\N
\.


--
-- Data for Name: route_operations; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.route_operations (id, route_id, operation_type_id, equipment_id, sequence_number, duration_minutes, notes, created_at, workshop_id, is_cooperation, prep_time, control_time, parts_count, coop_company_id, app_id, workshop_area_id, equipment_instance_id, fixture_id, cost_logistics, cost_operation, previous_operation_id, next_operation_id, total_time, coop_duration_days, coop_position) FROM stdin;
390	96	24	17	6	23		2026-04-22 14:28:20.88656	\N	f	2	1	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	26	0	start
391	97	16	7	1	4	\N	2026-04-22 14:44:49.21144	8	f	1	1	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	6	0	start
392	97	22	53	2	3	\N	2026-04-22 14:44:49.21229	6	f	1	1	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	5	0	start
393	97	21	34	3	3	\N	2026-04-22 14:44:49.213013	8	f	4	2	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	9	0	start
394	97	31	34	4	60	\N	2026-04-22 14:44:49.21396	8	f	2	3	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	65	0	start
395	97	24	51	5	27	фрезеровать лыски с ТП0,3	2026-04-22 14:44:49.214835	6	f	1	2	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	30	0	start
382	95	22	13	1	25	fuck_this_shit	2026-04-16 08:49:35.846857	6	f	5	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
363	87	13	19	1	15	\N	2026-04-11 19:07:03.494214	8	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	15	0	start
364	87	24	51	2	45	\N	2026-04-11 19:07:03.495927	6	f	10	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	65	0	start
381	95	31	\N	3	0		2026-04-16 08:49:35.846857	\N	t	0	0	1	3	\N	\N	\N	\N	\N	\N	\N	\N	0	6	start
383	95	24	30	2	15		2026-04-16 08:49:35.846857	6	f	10	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
366	88	22	48	2	30	\N	2026-04-11 19:12:19.462199	6	f	15	5	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	50	0	start
365	88	22	53	1	40	\N	2026-04-11 19:12:19.461174	6	f	5	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	55	0	start
367	88	24	51	3	55	\N	2026-04-11 19:12:19.463197	6	f	10	15	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	80	0	start
379	94	31	\N	2	0		2026-04-16 08:49:18.277509	\N	t	0	0	1	3	\N	\N	\N	\N	\N	\N	\N	\N	0	6	start
378	94	22	13	1	15		2026-04-16 08:49:18.277509	6	f	5	45	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
380	94	24	30	3	15		2026-04-16 08:49:18.277509	6	f	5	45	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
388	96	39	36	5	240		2026-04-16 13:49:26.565829	\N	f	5	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	245	0	start
406	100	16	7	1	2	нужно	2026-04-23 13:05:01.883449	8	f	1	1	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	4	0	start
407	100	22	50	2	3	сверлить отв.	2026-04-23 13:05:01.887313	6	f	1	1	5	\N	\N	\N	\N	\N	\N	\N	\N	\N	5	0	start
386	96	15	8	4	0	обязательно	2026-04-16 13:48:05.416677	\N	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
396	98	24	17	6	23		2026-04-23 12:30:32.325926	\N	f	2	1	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
397	98	39	36	5	240		2026-04-23 12:30:32.325926	\N	f	5	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
398	98	15	8	4	0	обязательно	2026-04-23 12:30:32.325926	\N	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
399	98	22	48	1	50		2026-04-23 12:30:32.325926	\N	f	30	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
400	98	31	\N	3	0		2026-04-23 12:30:32.325926	\N	t	0	0	1	3	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
401	98	25	35	2	20		2026-04-23 12:30:32.325926	6	f	10	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
408	101	13	19	1	2	\N	2026-04-23 13:41:37.665796	8	f	1	1	10	\N	\N	\N	\N	\N	\N	\N	\N	\N	4	0	start
409	101	21	34	2	0	\N	2026-04-23 13:41:37.667381	8	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
410	101	31	34	3	0	\N	2026-04-23 13:41:37.668837	8	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
411	101	36	34	4	0	\N	2026-04-23 13:41:37.669939	8	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
412	101	17	33	5	0	\N	2026-04-23 13:41:37.670985	7	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
413	101	37	32	6	0	\N	2026-04-23 13:41:37.671913	6	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
414	101	39	36	7	0	\N	2026-04-23 13:41:37.672662	8	f	0	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
372	93	22	13	2	15		2026-04-15 13:00:46.308271	6	f	5	40	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
377	93	31	\N	1	0		2026-04-15 14:10:46.28221	\N	t	0	0	1	3	\N	\N	\N	\N	\N	\N	\N	\N	0	6	start
373	93	24	30	3	5		2026-04-15 13:00:46.309424	6	f	15	40	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
387	96	22	48	1	50		2026-04-16 13:48:47.405077	\N	f	30	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	80	0	start
385	96	31	\N	3	0		2026-04-16 13:41:16.190241	\N	t	0	0	1	3	\N	\N	\N	\N	\N	\N	\N	\N	0	10	start
384	96	25	35	2	20		2026-04-16 13:40:17.924714	6	f	10	0	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
369	92	22	53	2	40		2026-04-11 23:04:07.777456	6	f	5	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
370	92	24	51	1	55	\N	2026-04-11 23:04:07.777456	6	f	10	15	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
368	92	22	48	3	30	\N	2026-04-11 23:04:07.777456	6	f	15	5	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
389	95	25	35	4	250		2026-04-21 13:13:54.088375	\N	f	30	10	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	start
\.


--
-- Data for Name: schedule_events; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.schedule_events (id, schedule_id, event_type, created_at, created_by) FROM stdin;
\.


--
-- Data for Name: sortament; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.sortament (id, app_id, name, gost, geometry_id, created_at) FROM stdin;
1	b35b566c	Квадрат	\N	9094b4bc	2026-02-20 21:07:36.073899
2	74ea7c28	Круг	\N	91910b8f	2026-02-20 21:07:36.073899
3	6b1bbecc	Лист	\N	c145677b	2026-02-20 21:07:36.073899
4	28593e67	Поковка круглая	\N	91910b8f	2026-02-20 21:07:36.073899
5	a3df9c38	Шестигранник	\N	b290ea0d	2026-02-20 21:07:36.073899
6	a4bd5798	Труба круглая	\N	abd1c863	2026-02-20 21:07:36.073899
7	c4fe4069	Фасонная заготовка	\N	c0ec2abd	2026-02-20 21:07:36.073899
8	abf3e627	Поковка прямоугольная	\N	c145677b	2026-02-20 21:07:36.073899
9	20e68eb9	Труба прямоугольная	\N	dc131627	2026-02-20 21:07:36.073899
10	f0035761	Труба квадратная	\N	d60d19ac	2026-02-20 21:07:36.073899
11	dfad2bbb	Пруток	\N	91910b8f	2026-02-20 21:07:36.073899
12	7ad65e6f	Полоса	\N	c145677b	2026-02-20 21:07:36.073899
13	b9d2585c	Плита	\N	c145677b	2026-02-20 21:07:36.073899
\.


--
-- Data for Name: system_parameters; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.system_parameters (id, app_id, name, value, description, param_type, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.tasks (id, app_id, order_id, operation_id, is_cooperation, coop_company_id, workshop_id, workshop_area_id, sequence_number, operation_type_id, equipment_instance_id, prep_time, duration_minutes, control_time, parts_count, notes, status, planned_date, actual_date, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.transactions (id, user_id, item_id, quantity, operation_type, detail, reason, "timestamp") FROM stdin;
\.


--
-- Data for Name: user_items; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.user_items (id, user_id, item_id, quantity, taken_at) FROM stdin;
1	\N	\N	1	2026-02-26 06:46:50.075835
2	\N	\N	2	2026-02-26 06:49:42.188462
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.users (id, username, password_hash, role, workstation, is_active, created_at, updated_at, workstations, screen_permissions, login) FROM stdin;
21	Братушкин Роман	$2b$12$9pFJz3kRmkIX6JgIDqcym.ZsU55V4YPk9yFxidkk/s.t8KZ7CtE/C	user	\N	t	2026-04-22 07:11:24.188592	2026-04-22 07:11:24.188595	["\\u0424\\u0440\\u0435\\u0437\\u0435\\u0440\\u043d\\u044b\\u0439 IMU-5x400_\\u21161", "\\u0424\\u0440\\u0435\\u0437\\u0435\\u0440\\u043d\\u044b\\u0439 IMU-5x400_\\u21162"]	\N	r.bratushkin
11	Александр	$2b$12$qpMxx.W2yRoVGXQaMSTZMe.HV0jR6FSpUO9oF2zWd31Do1Q8HOGKq	otk	\N	t	2026-04-17 00:47:38.733581	2026-04-17 09:03:36.762331	[]	[]	Максимов
8	Неменущий Алексей	$2b$12$v6a.2AEvSWFSaN1dLUOmTOonNptafsZm0Ku/H4A8fdSva96nVkTrq	foreman	\N	t	2026-02-27 05:19:58.832295	2026-04-14 10:42:48.345346	[]	["dashboard", "inventory", "details", "planner", "routes", "equipment"]	Неменущий Алексей
10	Пушкова Оксана	$2b$12$jMTVj2RqbjNya6I6qghbCOvnceUAQOdGZSf/j9xy/vylfNs3NQfgO	technologist_designer	\N	t	2026-04-07 08:32:38.124865	2026-04-24 09:28:50.005667	[]	{"screens": ["dashboard", "inventory", "details", "routes", "planning_calendar", "materials"], "route_view_mode": "approved_only"}	Пушкова Оксана
2	admin	$2b$12$S.YRI7PiiaPy9FkTm82o5OFDs7pl6SiNnrJ9Sf/GjC8.xouqj7lVm	admin	\N	t	2026-02-18 13:06:41.430394	2026-04-24 08:58:02.797409	[]	{"screens": ["dashboard", "inventory", "workshop_inventory", "transactions", "details", "routes", "planning", "planning_calendar", "planning_gantt", "planning_settings", "materials", "equipment", "reports", "import_export", "users"], "route_view_mode": "all"}	admin
\.


--
-- Data for Name: workshop_areas; Type: TABLE DATA; Schema: public; Owner: sklad_user
--

COPY public.workshop_areas (id, app_id, lotzman_id, workshop_id, designation, name, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: workshop_inventory; Type: TABLE DATA; Schema: public; Owner: romanbratushkin
--

COPY public.workshop_inventory (id, equipment_id, item_id, quantity, updated_at) FROM stdin;
34	48	875	1	2026-04-22 06:18:51.487987
36	51	349	2	2026-04-22 06:23:20.362592
\.


--
-- Data for Name: workshops; Type: TABLE DATA; Schema: public; Owner: romanbratuskin
--

COPY public.workshops (id, name, description, is_active, created_at, updated_at) FROM stdin;
6	Механический	6	t	2026-02-20 21:01:51.589282	2026-02-20 21:01:51.589282
7	Малярный	5	t	2026-02-20 21:01:51.589282	2026-02-20 21:01:51.589282
8	Заготовительный	9	t	2026-02-20 21:01:51.589282	2026-02-20 21:01:51.589282
\.


--
-- Name: audit_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.audit_log_id_seq', 1927, true);


--
-- Name: batch_counter_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.batch_counter_id_seq', 2, true);


--
-- Name: calendar_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.calendar_configs_id_seq', 22, true);


--
-- Name: cooperatives_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.cooperatives_id_seq', 3, true);


--
-- Name: detail_routes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.detail_routes_id_seq', 101, true);


--
-- Name: details_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.details_id_seq', 132, true);


--
-- Name: equipment_calendar_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.equipment_calendar_id_seq', 69, true);


--
-- Name: equipment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.equipment_id_seq', 57, true);


--
-- Name: equipment_instances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.equipment_instances_id_seq', 1, false);


--
-- Name: geometry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.geometry_id_seq', 13, true);


--
-- Name: inventory_changes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.inventory_changes_id_seq', 50, true);


--
-- Name: items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.items_id_seq', 930, true);


--
-- Name: material_instances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.material_instances_id_seq', 190, true);


--
-- Name: materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.materials_id_seq', 54, true);


--
-- Name: operation_cooperative_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.operation_cooperative_id_seq', 16, true);


--
-- Name: operation_equipment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.operation_equipment_id_seq', 98, true);


--
-- Name: operation_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.operation_types_id_seq', 39, true);


--
-- Name: operation_workshop_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.operation_workshop_id_seq', 28, true);


--
-- Name: order_priorities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.order_priorities_id_seq', 169, true);


--
-- Name: order_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.order_schedule_id_seq', 4, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.orders_id_seq', 90, true);


--
-- Name: planning_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.planning_rules_id_seq', 1, true);


--
-- Name: production_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.production_schedule_id_seq', 4408, true);


--
-- Name: route_operations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.route_operations_id_seq', 414, true);


--
-- Name: schedule_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.schedule_events_id_seq', 20, true);


--
-- Name: sortament_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.sortament_id_seq', 13, true);


--
-- Name: system_parameters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.system_parameters_id_seq', 1, false);


--
-- Name: tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.tasks_id_seq', 1, false);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.transactions_id_seq', 51, true);


--
-- Name: user_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.user_items_id_seq', 17, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.users_id_seq', 21, true);


--
-- Name: workshop_areas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sklad_user
--

SELECT pg_catalog.setval('public.workshop_areas_id_seq', 1, false);


--
-- Name: workshop_inventory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.workshop_inventory_id_seq', 36, true);


--
-- Name: workshop_inventory_new_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratushkin
--

SELECT pg_catalog.setval('public.workshop_inventory_new_id_seq', 1, true);


--
-- Name: workshops_id_seq; Type: SEQUENCE SET; Schema: public; Owner: romanbratuskin
--

SELECT pg_catalog.setval('public.workshops_id_seq', 8, true);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: batch_counter batch_counter_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.batch_counter
    ADD CONSTRAINT batch_counter_pkey PRIMARY KEY (id);


--
-- Name: batch_counter batch_counter_prefix_key; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.batch_counter
    ADD CONSTRAINT batch_counter_prefix_key UNIQUE (prefix);


--
-- Name: calendar_configs calendar_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.calendar_configs
    ADD CONSTRAINT calendar_configs_pkey PRIMARY KEY (id);


--
-- Name: cooperatives cooperatives_name_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.cooperatives
    ADD CONSTRAINT cooperatives_name_key UNIQUE (name);


--
-- Name: cooperatives cooperatives_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.cooperatives
    ADD CONSTRAINT cooperatives_pkey PRIMARY KEY (id);


--
-- Name: detail_routes detail_routes_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.detail_routes
    ADD CONSTRAINT detail_routes_pkey PRIMARY KEY (id);


--
-- Name: details details_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.details
    ADD CONSTRAINT details_pkey PRIMARY KEY (id);


--
-- Name: equipment equipment_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_app_id_key UNIQUE (app_id);


--
-- Name: equipment_calendar equipment_calendar_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.equipment_calendar
    ADD CONSTRAINT equipment_calendar_pkey PRIMARY KEY (id);


--
-- Name: equipment_instances equipment_instances_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment_instances
    ADD CONSTRAINT equipment_instances_app_id_key UNIQUE (app_id);


--
-- Name: equipment_instances equipment_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment_instances
    ADD CONSTRAINT equipment_instances_pkey PRIMARY KEY (id);


--
-- Name: equipment equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_pkey PRIMARY KEY (id);


--
-- Name: geometry geometry_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.geometry
    ADD CONSTRAINT geometry_app_id_key UNIQUE (app_id);


--
-- Name: geometry geometry_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.geometry
    ADD CONSTRAINT geometry_pkey PRIMARY KEY (id);


--
-- Name: inventory_changes inventory_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.inventory_changes
    ADD CONSTRAINT inventory_changes_pkey PRIMARY KEY (id);


--
-- Name: items items_item_id_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_id_key UNIQUE (item_id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: material_instances material_instances_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.material_instances
    ADD CONSTRAINT material_instances_app_id_key UNIQUE (app_id);


--
-- Name: material_instances material_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.material_instances
    ADD CONSTRAINT material_instances_pkey PRIMARY KEY (id);


--
-- Name: materials materials_name_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_name_key UNIQUE (name);


--
-- Name: materials materials_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_pkey PRIMARY KEY (id);


--
-- Name: operation_cooperative operation_cooperative_operation_type_id_cooperative_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_cooperative
    ADD CONSTRAINT operation_cooperative_operation_type_id_cooperative_id_key UNIQUE (operation_type_id, cooperative_id);


--
-- Name: operation_cooperative operation_cooperative_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_cooperative
    ADD CONSTRAINT operation_cooperative_pkey PRIMARY KEY (id);


--
-- Name: operation_equipment operation_equipment_operation_type_id_equipment_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_equipment
    ADD CONSTRAINT operation_equipment_operation_type_id_equipment_id_key UNIQUE (operation_type_id, equipment_id);


--
-- Name: operation_equipment operation_equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_equipment
    ADD CONSTRAINT operation_equipment_pkey PRIMARY KEY (id);


--
-- Name: operation_types operation_types_name_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.operation_types
    ADD CONSTRAINT operation_types_name_key UNIQUE (name);


--
-- Name: operation_types operation_types_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.operation_types
    ADD CONSTRAINT operation_types_pkey PRIMARY KEY (id);


--
-- Name: operation_workshop operation_workshop_operation_type_id_workshop_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_workshop
    ADD CONSTRAINT operation_workshop_operation_type_id_workshop_id_key UNIQUE (operation_type_id, workshop_id);


--
-- Name: operation_workshop operation_workshop_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_workshop
    ADD CONSTRAINT operation_workshop_pkey PRIMARY KEY (id);


--
-- Name: order_priorities order_priorities_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_priorities
    ADD CONSTRAINT order_priorities_pkey PRIMARY KEY (id);


--
-- Name: order_schedule order_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_schedule
    ADD CONSTRAINT order_schedule_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: planning_rules planning_rules_key_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.planning_rules
    ADD CONSTRAINT planning_rules_key_key UNIQUE (key);


--
-- Name: planning_rules planning_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.planning_rules
    ADD CONSTRAINT planning_rules_pkey PRIMARY KEY (id);


--
-- Name: production_schedule production_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.production_schedule
    ADD CONSTRAINT production_schedule_pkey PRIMARY KEY (id);


--
-- Name: route_operations route_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.route_operations
    ADD CONSTRAINT route_operations_pkey PRIMARY KEY (id);


--
-- Name: schedule_events schedule_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.schedule_events
    ADD CONSTRAINT schedule_events_pkey PRIMARY KEY (id);


--
-- Name: sortament sortament_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.sortament
    ADD CONSTRAINT sortament_app_id_key UNIQUE (app_id);


--
-- Name: sortament sortament_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.sortament
    ADD CONSTRAINT sortament_pkey PRIMARY KEY (id);


--
-- Name: system_parameters system_parameters_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.system_parameters
    ADD CONSTRAINT system_parameters_app_id_key UNIQUE (app_id);


--
-- Name: system_parameters system_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.system_parameters
    ADD CONSTRAINT system_parameters_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_app_id_key; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_app_id_key UNIQUE (app_id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: user_items user_items_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.user_items
    ADD CONSTRAINT user_items_pkey PRIMARY KEY (id);


--
-- Name: users users_login_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_login_key UNIQUE (login);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: workshop_areas workshop_areas_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.workshop_areas
    ADD CONSTRAINT workshop_areas_app_id_key UNIQUE (app_id);


--
-- Name: workshop_areas workshop_areas_pkey; Type: CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.workshop_areas
    ADD CONSTRAINT workshop_areas_pkey PRIMARY KEY (id);


--
-- Name: workshop_inventory workshop_inventory_new_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.workshop_inventory
    ADD CONSTRAINT workshop_inventory_new_pkey PRIMARY KEY (id);


--
-- Name: workshops workshops_name_key; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.workshops
    ADD CONSTRAINT workshops_name_key UNIQUE (name);


--
-- Name: workshops workshops_pkey; Type: CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.workshops
    ADD CONSTRAINT workshops_pkey PRIMARY KEY (id);


--
-- Name: idx_audit_log_action; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_audit_log_action ON public.audit_log USING btree (action);


--
-- Name: idx_audit_log_timestamp; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_audit_log_timestamp ON public.audit_log USING btree ("timestamp");


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_audit_log_user_id ON public.audit_log USING btree (user_id);


--
-- Name: idx_detail_routes_app_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_detail_routes_app_id ON public.detail_routes USING btree (app_id);


--
-- Name: idx_detail_routes_detail_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_detail_routes_detail_id ON public.detail_routes USING btree (detail_id);


--
-- Name: idx_equipment_instances_app_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_equipment_instances_app_id ON public.equipment_instances USING btree (app_id);


--
-- Name: idx_equipment_instances_equipment_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_equipment_instances_equipment_id ON public.equipment_instances USING btree (equipment_id);


--
-- Name: idx_inventory_changes_item_id; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_inventory_changes_item_id ON public.inventory_changes USING btree (item_id);


--
-- Name: idx_inventory_changes_timestamp; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_inventory_changes_timestamp ON public.inventory_changes USING btree ("timestamp");


--
-- Name: idx_items_item_id; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_items_item_id ON public.items USING btree (item_id);


--
-- Name: idx_items_low_stock; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_items_low_stock ON public.items USING btree (quantity) WHERE (quantity <= min_stock);


--
-- Name: idx_items_name; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_items_name ON public.items USING btree (name);


--
-- Name: idx_material_instances_lotzman_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_material_instances_lotzman_id ON public.material_instances USING btree (lotzman_id);


--
-- Name: idx_material_instances_volume_argument; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_material_instances_volume_argument ON public.material_instances USING btree (volume_argument);


--
-- Name: idx_order_schedule_date; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX idx_order_schedule_date ON public.order_schedule USING btree (schedule_date);


--
-- Name: idx_order_schedule_order_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX idx_order_schedule_order_id ON public.order_schedule USING btree (order_id);


--
-- Name: idx_route_operations_app_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_route_operations_app_id ON public.route_operations USING btree (app_id);


--
-- Name: idx_route_operations_workshop_area_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_route_operations_workshop_area_id ON public.route_operations USING btree (workshop_area_id);


--
-- Name: idx_system_parameters_app_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_system_parameters_app_id ON public.system_parameters USING btree (app_id);


--
-- Name: idx_system_parameters_name; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_system_parameters_name ON public.system_parameters USING btree (name);


--
-- Name: idx_tasks_app_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX idx_tasks_app_id ON public.tasks USING btree (app_id);


--
-- Name: idx_tasks_order_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX idx_tasks_order_id ON public.tasks USING btree (order_id);


--
-- Name: idx_tasks_workshop_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX idx_tasks_workshop_id ON public.tasks USING btree (workshop_id);


--
-- Name: idx_transactions_item_id; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_transactions_item_id ON public.transactions USING btree (item_id);


--
-- Name: idx_transactions_timestamp; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_transactions_timestamp ON public.transactions USING btree ("timestamp");


--
-- Name: idx_transactions_type; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_transactions_type ON public.transactions USING btree (operation_type);


--
-- Name: idx_transactions_user_id; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_transactions_user_id ON public.transactions USING btree (user_id);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: romanbratuskin
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: idx_workshop_areas_app_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_workshop_areas_app_id ON public.workshop_areas USING btree (app_id);


--
-- Name: idx_workshop_areas_workshop_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX idx_workshop_areas_workshop_id ON public.workshop_areas USING btree (workshop_id);


--
-- Name: ix_details_designation; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_details_designation ON public.details USING btree (designation);


--
-- Name: ix_details_detail_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE UNIQUE INDEX ix_details_detail_id ON public.details USING btree (detail_id);


--
-- Name: ix_details_lotzman_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_details_lotzman_id ON public.details USING btree (lotzman_id);


--
-- Name: ix_equipment_calendar_date; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_equipment_calendar_date ON public.equipment_calendar USING btree (date);


--
-- Name: ix_equipment_calendar_equipment_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_equipment_calendar_equipment_id ON public.equipment_calendar USING btree (equipment_id);


--
-- Name: ix_order_priorities_order_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE UNIQUE INDEX ix_order_priorities_order_id ON public.order_priorities USING btree (order_id);


--
-- Name: ix_production_schedule_order_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_production_schedule_order_id ON public.production_schedule USING btree (order_id);


--
-- Name: ix_production_schedule_planned_date; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_production_schedule_planned_date ON public.production_schedule USING btree (planned_date);


--
-- Name: ix_production_schedule_status; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_production_schedule_status ON public.production_schedule USING btree (status);


--
-- Name: ix_schedule_events_schedule_id; Type: INDEX; Schema: public; Owner: sklad_user
--

CREATE INDEX ix_schedule_events_schedule_id ON public.schedule_events USING btree (schedule_id);


--
-- Name: ix_user_items_item_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_user_items_item_id ON public.user_items USING btree (item_id);


--
-- Name: ix_user_items_user_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_user_items_user_id ON public.user_items USING btree (user_id);


--
-- Name: ix_workshop_inventory_equipment_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_workshop_inventory_equipment_id ON public.workshop_inventory USING btree (equipment_id);


--
-- Name: ix_workshop_inventory_item_id; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE INDEX ix_workshop_inventory_item_id ON public.workshop_inventory USING btree (item_id);


--
-- Name: unique_equipment_date; Type: INDEX; Schema: public; Owner: romanbratushkin
--

CREATE UNIQUE INDEX unique_equipment_date ON public.equipment_calendar USING btree (equipment_id, date);


--
-- Name: items update_items_updated_at; Type: TRIGGER; Schema: public; Owner: romanbratuskin
--

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON public.items FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: romanbratuskin
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: audit_log audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: calendar_configs calendar_configs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.calendar_configs
    ADD CONSTRAINT calendar_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: detail_routes detail_routes_detail_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.detail_routes
    ADD CONSTRAINT detail_routes_detail_id_fkey FOREIGN KEY (detail_id) REFERENCES public.details(id);


--
-- Name: details details_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.details
    ADD CONSTRAINT details_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: equipment_calendar equipment_calendar_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.equipment_calendar
    ADD CONSTRAINT equipment_calendar_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id) ON DELETE CASCADE;


--
-- Name: equipment_instances equipment_instances_operator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment_instances
    ADD CONSTRAINT equipment_instances_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id);


--
-- Name: equipment equipment_operator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.equipment
    ADD CONSTRAINT equipment_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.users(id);


--
-- Name: inventory_changes inventory_changes_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.inventory_changes
    ADD CONSTRAINT inventory_changes_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: inventory_changes inventory_changes_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.inventory_changes
    ADD CONSTRAINT inventory_changes_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: operation_cooperative operation_cooperative_cooperative_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_cooperative
    ADD CONSTRAINT operation_cooperative_cooperative_id_fkey FOREIGN KEY (cooperative_id) REFERENCES public.cooperatives(id);


--
-- Name: operation_cooperative operation_cooperative_operation_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_cooperative
    ADD CONSTRAINT operation_cooperative_operation_type_id_fkey FOREIGN KEY (operation_type_id) REFERENCES public.operation_types(id);


--
-- Name: operation_equipment operation_equipment_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_equipment
    ADD CONSTRAINT operation_equipment_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: operation_equipment operation_equipment_operation_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_equipment
    ADD CONSTRAINT operation_equipment_operation_type_id_fkey FOREIGN KEY (operation_type_id) REFERENCES public.operation_types(id);


--
-- Name: operation_workshop operation_workshop_operation_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_workshop
    ADD CONSTRAINT operation_workshop_operation_type_id_fkey FOREIGN KEY (operation_type_id) REFERENCES public.operation_types(id);


--
-- Name: operation_workshop operation_workshop_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.operation_workshop
    ADD CONSTRAINT operation_workshop_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshops(id);


--
-- Name: order_priorities order_priorities_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_priorities
    ADD CONSTRAINT order_priorities_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_schedule order_schedule_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.order_schedule
    ADD CONSTRAINT order_schedule_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: orders orders_route_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_route_id_fkey FOREIGN KEY (route_id) REFERENCES public.detail_routes(id) ON DELETE CASCADE;


--
-- Name: production_schedule production_schedule_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.production_schedule
    ADD CONSTRAINT production_schedule_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id) ON DELETE SET NULL;


--
-- Name: production_schedule production_schedule_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.production_schedule
    ADD CONSTRAINT production_schedule_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: production_schedule production_schedule_route_operation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.production_schedule
    ADD CONSTRAINT production_schedule_route_operation_id_fkey FOREIGN KEY (route_operation_id) REFERENCES public.route_operations(id) ON DELETE CASCADE;


--
-- Name: route_operations route_operations_route_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.route_operations
    ADD CONSTRAINT route_operations_route_id_fkey FOREIGN KEY (route_id) REFERENCES public.detail_routes(id) ON DELETE CASCADE;


--
-- Name: schedule_events schedule_events_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.schedule_events
    ADD CONSTRAINT schedule_events_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.production_schedule(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_coop_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_coop_company_id_fkey FOREIGN KEY (coop_company_id) REFERENCES public.cooperatives(id);


--
-- Name: tasks tasks_operation_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_operation_type_id_fkey FOREIGN KEY (operation_type_id) REFERENCES public.operation_types(id);


--
-- Name: tasks tasks_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshops(id);


--
-- Name: transactions transactions_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratuskin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_items user_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.user_items
    ADD CONSTRAINT user_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: user_items user_items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.user_items
    ADD CONSTRAINT user_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workshop_areas workshop_areas_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sklad_user
--

ALTER TABLE ONLY public.workshop_areas
    ADD CONSTRAINT workshop_areas_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshops(id);


--
-- Name: workshop_inventory workshop_inventory_new_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.workshop_inventory
    ADD CONSTRAINT workshop_inventory_new_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment(id);


--
-- Name: workshop_inventory workshop_inventory_new_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: romanbratushkin
--

ALTER TABLE ONLY public.workshop_inventory
    ADD CONSTRAINT workshop_inventory_new_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO sklad_user;


--
-- Name: TABLE audit_log; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.audit_log TO sklad_app;
GRANT ALL ON TABLE public.audit_log TO sklad_user;


--
-- Name: SEQUENCE audit_log_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.audit_log_id_seq TO sklad_app;
GRANT ALL ON SEQUENCE public.audit_log_id_seq TO sklad_user;


--
-- Name: TABLE batch_counter; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.batch_counter TO sklad_user;


--
-- Name: SEQUENCE batch_counter_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.batch_counter_id_seq TO sklad_user;


--
-- Name: TABLE calendar_configs; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.calendar_configs TO sklad_user;


--
-- Name: SEQUENCE calendar_configs_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.calendar_configs_id_seq TO sklad_user;


--
-- Name: TABLE transactions; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.transactions TO sklad_app;
GRANT ALL ON TABLE public.transactions TO sklad_user;


--
-- Name: TABLE daily_transaction_stats; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.daily_transaction_stats TO sklad_user;


--
-- Name: TABLE details; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.details TO sklad_user;


--
-- Name: SEQUENCE details_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.details_id_seq TO sklad_user;


--
-- Name: TABLE equipment_calendar; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.equipment_calendar TO sklad_user;


--
-- Name: SEQUENCE equipment_calendar_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.equipment_calendar_id_seq TO sklad_user;


--
-- Name: TABLE inventory_changes; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.inventory_changes TO sklad_app;
GRANT ALL ON TABLE public.inventory_changes TO sklad_user;


--
-- Name: SEQUENCE inventory_changes_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.inventory_changes_id_seq TO sklad_app;
GRANT ALL ON SEQUENCE public.inventory_changes_id_seq TO sklad_user;


--
-- Name: TABLE items; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.items TO sklad_app;
GRANT ALL ON TABLE public.items TO sklad_user;


--
-- Name: SEQUENCE items_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.items_id_seq TO sklad_app;
GRANT ALL ON SEQUENCE public.items_id_seq TO sklad_user;


--
-- Name: TABLE low_stock_items; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.low_stock_items TO sklad_user;


--
-- Name: TABLE materials; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.materials TO sklad_user;


--
-- Name: SEQUENCE materials_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.materials_id_seq TO sklad_user;


--
-- Name: TABLE operation_types; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.operation_types TO sklad_user;


--
-- Name: SEQUENCE operation_types_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.operation_types_id_seq TO sklad_user;


--
-- Name: TABLE order_priorities; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.order_priorities TO sklad_user;


--
-- Name: SEQUENCE order_priorities_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.order_priorities_id_seq TO sklad_user;


--
-- Name: TABLE order_schedule; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.order_schedule TO sklad_user;


--
-- Name: SEQUENCE order_schedule_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.order_schedule_id_seq TO sklad_user;


--
-- Name: TABLE orders; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.orders TO sklad_user;


--
-- Name: SEQUENCE orders_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.orders_id_seq TO sklad_user;


--
-- Name: TABLE production_schedule; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.production_schedule TO sklad_user;


--
-- Name: SEQUENCE production_schedule_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.production_schedule_id_seq TO sklad_user;


--
-- Name: TABLE tasks; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.tasks TO sklad_user;


--
-- Name: SEQUENCE tasks_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.tasks_id_seq TO sklad_user;


--
-- Name: SEQUENCE transactions_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.transactions_id_seq TO sklad_app;
GRANT ALL ON SEQUENCE public.transactions_id_seq TO sklad_user;


--
-- Name: TABLE user_items; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.user_items TO sklad_user;


--
-- Name: SEQUENCE user_items_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.user_items_id_seq TO sklad_user;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.users TO sklad_app;
GRANT ALL ON TABLE public.users TO sklad_user;


--
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.users_id_seq TO sklad_app;
GRANT ALL ON SEQUENCE public.users_id_seq TO sklad_user;


--
-- Name: SEQUENCE workshop_inventory_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.workshop_inventory_id_seq TO sklad_user;


--
-- Name: TABLE workshop_inventory; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON TABLE public.workshop_inventory TO sklad_user;


--
-- Name: SEQUENCE workshop_inventory_new_id_seq; Type: ACL; Schema: public; Owner: romanbratushkin
--

GRANT ALL ON SEQUENCE public.workshop_inventory_new_id_seq TO sklad_user;


--
-- Name: TABLE workshops; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON TABLE public.workshops TO sklad_user;


--
-- Name: SEQUENCE workshops_id_seq; Type: ACL; Schema: public; Owner: romanbratuskin
--

GRANT ALL ON SEQUENCE public.workshops_id_seq TO sklad_user;


--
-- PostgreSQL database dump complete
--

\unrestrict YH0Uf9D4cJE3MeTmB6tbCkgMRBXVBJ0c35Vu9T7PqNAsEASAd4eSrFDo5LEGhnx

