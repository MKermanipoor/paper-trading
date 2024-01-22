CREATE TYPE transaction_type AS ENUM ('buy', 'sell');

create table orders(
    id serial not null primary key ,
    shares real not null,
    average_price real not null,
    action_time timestamp not null default now(),
    filled_at timestamp not null default now(),
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
    start_time timestamp not null default now(),
    end_time timestamp,
    account_id int not null,
    setting jsonb not null,
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