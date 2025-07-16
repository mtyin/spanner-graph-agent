CREATE TABLE IF NOT EXISTS Person(
  id STRING(MAX) NOT NULL,
  name STRING(MAX),
  birthday DATE,
) PRIMARY KEY (id);

CREATE TABLE IF NOT EXISTS Company(
  id STRING(MAX) NOT NULL,
  name STRING(MAX),
  address STRING(MAX),
  date_founded DATE,
) PRIMARY KEY (id);

CREATE TABLE IF NOT EXISTS MutualFund(
  id STRING(MAX) NOT NULL,
  name STRING(MAX),
) PRIMARY KEY (id);

CREATE TABLE IF NOT EXISTS Employment(
  id STRING(MAX) NOT NULL,
  employee_id STRING(MAX) NOT NULL,
  job_title STRING(MAX),
  FOREIGN KEY (employee_id) REFERENCES Person(id),
) PRIMARY KEY (id, employee_id), INTERLEAVE IN PARENT Company;

CREATE TABLE IF NOT EXISTS Investment(
  id STRING(MAX) NOT NULL,
  investor_id STRING(MAX) NOT NULL,
  stock_ticker STRING(6),
  release_date DATE,
  num_shares FLOAT32,
  percentage_holding FLOAT32,
) PRIMARY KEY (id, investor_id, stock_ticker, release_date),
  INTERLEAVE IN PARENT Company;

CREATE PROPERTY GRAPH IF NOT EXISTS FinanceGraph
NODE TABLES (
  Company,
  MutualFund,
  Person,
)
EDGE TABLES (
  Investment AS Person_Investment
    SOURCE KEY(investor_id) REFERENCES Person(id)
    DESTINATION KEY(id) REFERENCES Company(id)
    LABEL ownsShare PROPERTIES (id AS company_id,
                                investor_id,
                                stock_ticker,
                                release_date,
                                num_shares,
                                percentage_holding),
  Investment AS Company_Investment
    SOURCE KEY(investor_id) REFERENCES Company(id)
    DESTINATION KEY(id) REFERENCES Company(id)
    LABEL ownsShare PROPERTIES (id AS company_id,
                                investor_id,
                                stock_ticker,
                                release_date,
                                num_shares,
                                percentage_holding),
  Investment AS MutualFund_Investment
    SOURCE KEY(investor_id) REFERENCES MutualFund(id)
    DESTINATION KEY(id) REFERENCES Company(id)
    LABEL ownsShare PROPERTIES (id AS company_id,
                                investor_id,
                                stock_ticker,
                                release_date,
                                num_shares,
                                percentage_holding),
  Employment
    SOURCE KEY(employee_id) REFERENCES Person(id)
    DESTINATION KEY(id) REFERENCES Company(id)
    LABEL worksAt PROPERTIES (id AS company_id,
                              employee_id,
                              job_title),
);
