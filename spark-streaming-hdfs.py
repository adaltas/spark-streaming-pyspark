'''
Submit from master02.cluster as spark user:

spark-submit \
--master yarn --deploy-mode client \
--num-executors 2 --executor-cores 1 \
--executor-memory 5g --driver-memory 4g \
--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.3.0 \
--conf spark.sql.hive.thriftServer.singleSession=true \
/vagrant/spark-streaming-hdfs.py

* The application reads data from Kafka topic, parses Kafka messages, and dumps unaltered raw data to HDFS
* Two streaming queries
    * `PersistRawTaxiRides` query persists raw taxi rides data on hdfs path /user/spark/datalake/RidesRaw
    * `PersistRawTaxiFares` query persists raw taxi fares data on hdfs path /user/spark/datalake/FaresRaw

'''
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import expr
from pyspark.sql.functions import avg
from pyspark.sql.functions import window

def parse_data_from_kafka_message(sdf, schema):
    from pyspark.sql.functions import split
    assert sdf.isStreaming == True, "DataFrame doesn't receive treaming data"
    col = split(sdf['value'], ',') #split attributes to nested array in one Column
    #now expand col to multiple top-level columns
    for idx, field in enumerate(schema): 
        sdf = sdf.withColumn(field.name, col.getItem(idx).cast(field.dataType))
    return sdf.select([field.name for field in schema])
    
spark = SparkSession.builder \
    .appName("Spark Structured Streaming from Kafka") \
    .getOrCreate()

sdfRides = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "master02.cluster:6667") \
    .option("subscribe", "taxirides") \
    .option("startingOffsets", "latest") \
    .load() \
    .selectExpr("CAST(value AS STRING)") 

sdfFares = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "master02.cluster:6667") \
    .option("subscribe", "taxifares") \
    .option("startingOffsets", "latest") \
    .load() \
    .selectExpr("CAST(value AS STRING)")
    
taxiFaresSchema = StructType([ \
    StructField("rideId", LongType()), StructField("taxiId", LongType()), \
    StructField("driverId", LongType()), StructField("startTime", TimestampType()), \
    StructField("paymentType", StringType()), StructField("tip", FloatType()), \
    StructField("tolls", FloatType()), StructField("totalFare", FloatType())])
    
taxiRidesSchema = StructType([ \
    StructField("rideId", LongType()), StructField("isStart", StringType()), \
    StructField("endTime", TimestampType()), StructField("startTime", TimestampType()), \
    StructField("startLon", FloatType()), StructField("startLat", FloatType()), \
    StructField("endLon", FloatType()), StructField("endLat", FloatType()), \
    StructField("passengerCnt", ShortType()), StructField("taxiId", LongType()), \
    StructField("driverId", LongType())])

sdfRides = parse_data_from_kafka_message(sdfRides, taxiRidesSchema)
sdfFares = parse_data_from_kafka_message(sdfFares, taxiFaresSchema)

from pyspark.sql.functions import year, month, dayofmonth


sdfRides.withColumn("year", year("startTime")) \
    .withColumn("month", month("startTime")) \
    .withColumn("day", dayofmonth("startTime")) \
    .writeStream \
    .queryName("PersistRawTaxiRides") \
    .outputMode("append") \
    .format("parquet") \
    .option("path", "datalake/RidesRaw") \
    .option("checkpointLocation", "checkpoints/RidesRaw") \
    .partitionBy("startTime") \
    .option("truncate", False) \
    .start()

sdfFares.withColumn("year", year("startTime")) \
    .withColumn("month", month("startTime")) \
    .withColumn("day", dayofmonth("startTime")) \
    .writeStream \
    .queryName("PersistRawTaxiFares") \
    .outputMode("append") \
    .format("parquet") \
    .option("path", "datalake/FaresRaw") \
    .option("checkpointLocation", "checkpoints/FaresRaw") \
    .partitionBy("year", "month", "day") \
    .option("truncate", False) \
    .start()    
    
#Notice that the path `checkpoints/FaresRaw` amounts to `/user/spark/datalake/FaresRaw` on HDFS
