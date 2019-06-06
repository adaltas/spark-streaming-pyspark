'''
Submit from master02.cluster as spark user:

spark-submit \
--master yarn --deploy-mode client \
--num-executors 2 --executor-cores 1 \
--executor-memory 5g --driver-memory 4g \
--packages org.apache.spark:spark-sql-kafka-0-10_2.11:2.3.0 \
--conf spark.sql.hive.thriftServer.singleSession=true \
/vagrant/spark-streaming-memory.py

* The application reads data from Kafka topic, parses Kafka messages, dumps unaltered raw data to HDFS, processes data, and mounts the results in memory
* Embedeed Spark Thrift Server is launched to expose streaming results stored in memory
* Three streaming queries
    * `PersistRawTaxiRides` query persists raw taxi rides data on hdfs path /user/spark/datalake/RidesRaw
    * `PersistRawTaxiFares` query persists raw taxi fares data on hdfs path /user/spark/datalake/FaresRaw
    * `TipsInMemory` query writes the streaming results in-memory of the Spark Driver

'''
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import expr
from pyspark.sql.functions import avg
from pyspark.sql.functions import window

def isPointInPath(x, y, poly):
    """check if point x, y is in poly
    poly -- a list of tuples [(x, y), (x, y), ...]"""
    num = len(poly)
    i = 0
    j = num - 1
    c = False
    for i in range(num):
        if ((poly[i][1] > y) != (poly[j][1] > y)) and \
                (x < poly[i][0] + (poly[j][0] - poly[i][0]) * (y - poly[i][1]) /
                                  (poly[j][1] - poly[i][1])):
            c = not c
        j = i
    return c

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
    
# Data cleaning
LON_EAST, LON_WEST, LAT_NORTH, LAT_SOUTH = -73.7, -74.05, 41.0, 40.5
sdfRides = sdfRides.filter( \
    sdfRides["startLon"].between(LON_WEST, LON_EAST) & \
    sdfRides["startLat"].between(LAT_SOUTH, LAT_NORTH) & \
    sdfRides["endLon"].between(LON_WEST, LON_EAST) & \
    sdfRides["endLat"].between(LAT_SOUTH, LAT_NORTH))
sdfRides = sdfRides.filter(sdfRides["isStart"] == "END") #Keep only finished!

# Apply watermarks on event-time columns
sdfFaresWithWatermark = sdfFares \
    .selectExpr("rideId AS rideId_fares", "startTime", "totalFare", "tip") \
    .withWatermark("startTime", "30 minutes")  # maximal delay

sdfRidesWithWatermark = sdfRides \
  .selectExpr("rideId", "endTime", "driverId", "taxiId", \
    "startLon", "startLat", "endLon", "endLat") \
  .withWatermark("endTime", "30 minutes") # maximal delay

# Join with event-time constraints and aggregate
sdf = sdfFaresWithWatermark \
    .join(sdfRidesWithWatermark, \
      expr(""" 
       rideId_fares = rideId AND 
        endTime > startTime AND
        endTime <= startTime + interval 2 hours
        """))

# Feature engineering neighborhoods
nbhds_df = spark.read.json("file:///vagrant/NYC_neighborhoods/nbhd.jsonl") # nbhd.jsonl file has to be available!
lookupdict = nbhds_df.select("name","coord").rdd.collectAsMap()
broadcastVar = spark.sparkContext.broadcast(lookupdict) #use broadcastVar.value from now on
manhattan_bbox = [[-74.0489866963,40.681530375],[-73.8265135518,40.681530375],[-73.8265135518,40.9548628598],[-74.0489866963,40.9548628598],[-74.0489866963,40.681530375]]
from pyspark.sql.functions import udf
def find_nbhd(lon, lat):
  '''takes geo point as lon, lat floats and returns name of neighborhood it belongs to
  needs broadcastVar available'''
  if not isPointInPath(lon, lat, manhattan_bbox) : return "Other"
  for name, coord in broadcastVar.value.items():
    if isPointInPath(lon, lat, coord):
      return str(name) #cast unicode->str
  return "Other" #geo-point not in neighborhoods
find_nbhd_udf = udf(find_nbhd, StringType())
sdf = sdf.withColumn("stopNbhd", find_nbhd_udf("endLon", "endLat"))
sdf = sdf.withColumn("startNbhd", find_nbhd_udf("startLon", "startLat"))

# Aggregate
tips = sdf \
    .groupBy(
        window("endTime", "30 minutes", "10 minutes"),
        "stopNbhd") \
    .agg(avg("tip").alias("avgtip"))

# Launch Spark Thrift Server
from py4j.java_gateway import java_import
java_import(spark.sparkContext._gateway.jvm, "")
spark.sparkContext._gateway.jvm.org.apache.spark.sql.hive.thriftserver \
  .HiveThriftServer2.startWithContext(spark._jwrapped)

# Write streaming results in memory
tips.writeStream \
    .queryName("TipsInMemory") \
    .outputMode("append") \
    .format("memory") \
    .option("truncate", False) \
    .start() \
