import sys

import mlflow.pyfunc
from pyspark.sql import SparkSession

FEATURES = ["tenure_months", "monthly_charges", "support_calls"]


def main(input_path: str, output_path: str) -> None:
    spark = SparkSession.builder.getOrCreate()
    # モデルを各 executor に配り、Pandas UDF として列単位で推論する
    predict = mlflow.pyfunc.spark_udf(
        spark, "models:/churn-classifier@champion", result_type="array<double>"
    )
    df = spark.read.parquet(input_path)
    scored = df.withColumn("churn_probability", predict(*FEATURES)[1])
    scored.write.mode("overwrite").parquet(output_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
