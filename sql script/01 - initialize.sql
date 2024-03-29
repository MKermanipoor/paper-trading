CREATE TYPE transaction_type AS ENUM ('buy', 'sell');

create table orders(
    id serial not null primary key ,
    shares float8,
    average_price real,
    action_time timestamp not null default now(),
    filled_at timestamp,
    type transaction_type not null,
    alpaca_id uuid not null,
    rule_id int not null
);

create table accounts(
    id serial not null primary key,
    title text not null,
    api_key text not null,
    secret_key text not null
);

create table assets(
    id serial primary key ,
    symbol text not null
);

create table test_info(
    id serial primary key ,
    name text not null,
    start_time timestamp not null default now(),
    end_time timestamp,
    account_id int not null,
    sell_interval jsonb not null,
    buy_interval jsonb not null,
    setting jsonb not null
);

create table assets_budget(
    id serial,
    budget real not null,
    initial_budget real not null,
    asset_id int not null,
    test_id int not null
);

create table rules(
    id serial not null primary key,
    setting jsonb,
    asset_id int not null,
    position transaction_type not null,
    test_id int not null
);