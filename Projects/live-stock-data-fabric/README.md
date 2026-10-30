# Real-Time Intelligence in Microsoft Fabric

## Project Overview

This project documents my completion of the **Get started with Real-Time Intelligence in Microsoft Fabric** lab. The goal of the exercise was to build a small end-to-end real-time analytics solution using a live stock market data stream.

During the lab, I used Microsoft Fabric to ingest streaming stock data, store it in an Eventhouse, analyze it with Kusto Query Language (KQL), visualize changing prices in a real-time dashboard, and configure an alert with Activator.

## What I Built

The completed solution followed this flow:

1. Connected to the built-in stock market sample data.
2. Created an Eventstream to ingest the incoming events.
3. Created an Eventhouse and KQL database to store and query the data.
4. Routed the Eventstream into a `stock` table.
5. Queried recent stock records with KQL.
6. Calculated the average bid price for each stock symbol over the previous five minutes.
7. Created a real-time dashboard with a column chart.
8. Enabled live refresh for the dashboard.
9. Configured an Activator alert based on a change in average stock price.

## Architecture

```text
Stock Market Sample Data
          |
          v
      Eventstream
          |
          v
 Eventhouse / KQL Database
          |
          v
       stock Table
          |
          v
      KQL Queries
          |
          v
 Real-Time Dashboard
          |
          v
    Activator Alert
```

## Implementation

### 1. Ingested the Stock Market Stream

I opened the Real-Time hub in Microsoft Fabric and selected the built-in **Stock market** sample source. I then created an Eventstream named `stock-data` to receive the streaming data.

![Stock data import](./00-stock%20data%20import.png)

### 2. Created the Eventstream

The Eventstream provided the ingestion layer for the solution. It connected the `stock` source to the automatically created `stock-data-stream` and provided a visual representation of the data flow.

![Stock data Eventstream](./01-stock%20data%20eventstream.png)

### 3. Stored the Data in an Eventhouse

I created an Eventhouse with an associated KQL database. Inside the database, I created a table named `stock` and configured the existing Eventstream as its data source. This allowed the incoming events to be stored and made available for analysis.

### 4. Queried the Streaming Data with KQL

I first validated the ingestion process by returning a sample of 100 rows:

```kusto
stock
| take 100
```

I then calculated the average bid price for each stock symbol using only records received during the previous five minutes:

```kusto
stock
| where todatetime(["time"]) > ago(5m)
| summarize avgPrice = avg(todecimal(bidPrice)) by symbol
| project symbol, avgPrice
```

Because the Eventstream continued to ingest data, rerunning the query produced updated averages as new records arrived.

![Average stock prices](./03-stock%20data%20avg%20prices.png)

### 5. Built a Real-Time Dashboard

I saved the average-price query to a new dashboard and displayed the results as a column chart. I also enabled live refresh with a 10-second refresh-rate limit so the visualization could update as the underlying stock data changed.

![Real-time stock dashboard](./04-stock%20data%20graph.png)

### 6. Configured an Activator Alert

Finally, I used Activator to create an alert grouped by stock symbol. The lab configuration checks the `avgPrice` value every five minutes and can send an email when the average price increases by the configured threshold.

## Technologies Used

- Microsoft Fabric
- Real-Time hub
- Eventstream
- Eventhouse
- KQL database
- Kusto Query Language (KQL)
- Real-Time Dashboard
- Activator

## What I Learned

This exercise helped me understand how the Microsoft Fabric Real-Time Intelligence components work together in an end-to-end streaming solution. In particular, I practiced:

- Connecting Fabric to a streaming data source.
- Moving real-time events through an Eventstream.
- Persisting streaming records in an Eventhouse table.
- Writing KQL queries against continuously arriving data.
- Creating time-windowed aggregations.
- Building a dashboard that refreshes as the source data changes.
- Using Activator to monitor query results and trigger a notification.

## Training Resource

This project was completed by following the Microsoft Learn lab:

[Get started with Real-Time Intelligence in Microsoft Fabric](https://microsoftlearning.github.io/mslearn-fabric/Instructions/Labs/07-real-time-Intelligence.html)

## Repository Notes

The screenshots referenced in this README should be stored in the same directory as this file:

```text
README.md
00-stock data import.png
01-stock data eventstream.png
03-stock data avg prices.png
04-stock data graph.png
```

> This repository documents a training exercise and uses sample stock market data. It is intended to demonstrate the Microsoft Fabric workflow rather than provide investment analysis or trading guidance.
