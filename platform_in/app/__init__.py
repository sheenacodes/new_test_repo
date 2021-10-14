from flask import Flask
import os
import sys
from flask import jsonify
from elasticapm.contrib.flask import ElasticAPM
import logging
from flask import jsonify, request
import json
import certifi
from kafka import KafkaProducer
import sentry_sdk

from sentry_sdk.integrations.flask import FlaskIntegration

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), integrations=[FlaskIntegration()])


success_response_object = {"status": "success"}
success_code = 202
failure_response_object = {"status": "failure"}
failure_code = 400


def create_app(script_info=None):

    # instantiate the app
    app = Flask(__name__)

    # set config
    app_settings = os.getenv("APP_SETTINGS")
    app.config.from_object(app_settings)

    logging.basicConfig(level=app.config["LOG_LEVEL"])
    logging.getLogger().setLevel(app.config["LOG_LEVEL"])

    producer = KafkaProducer(
        bootstrap_servers=app.config["KAFKA_BROKERS"],
        security_protocol=app.config["SECURITY_PROTOCOL"],
        ssl_cafile=app.config["CA_FILE"],
        ssl_certfile=app.config["CERT_FILE"],
        ssl_keyfile=app.config["KEY_FILE"],
        value_serializer=lambda v: json.dumps(v).encode("ascii"),
        key_serializer=lambda v: json.dumps(v).encode("ascii"),
    )

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {"app": app}

    @app.route("/")
    def hello_world():
        return jsonify(health="ok")

    @app.route("/debug-sentry")
    def trigger_error():
        division_by_zero = 1 / 0

    @app.route("/c2/v1/<id>", methods=["POST"])
    def post_measurement_data(id):

        try:
            # data = request.get_data()
            data = request.get_data()
            logging.info(f"post data goes like : {data[0:200]}")
            logging.debug(f"post data in json : {json.loads(data)}")

            # Asynchronously produce a message, the delivery report callback
            # will be triggered from poll() above, or flush() below, when the message has
            # been successfully delivered or failed permanently.

            received_data = json.loads(data)

            key = "fixme"
            if "data" in received_data.keys():
                # received measurement type data

                bad_json = received_data["data"]
                timestamps = bad_json.keys()
                timestamp_value_pairs = []
                for item in timestamps:
                    if bad_json[item] != "0":
                        timestamp_value_pairs.append(
                            {"timestamp": item, "value": bad_json[item]}
                        )

                received_data["data"] = timestamp_value_pairs
                logging.info(received_data)
                producer.send(
                    topic="finest.json.c2lights.measurements",
                    key=id,
                    value=received_data,
                )

            elif "ref" in received_data.keys():
                # received alarm or event type data

                producer.send(
                    topic="finest.json.c2lights.events",
                    key=id,
                    value=request.get_json(),
                )

            return success_response_object, success_code

        except Exception as e:
            producer.flush()
            logging.error("post data error", exc_info=True)
            # elastic_apm.capture_exception()
            return failure_response_object, failure_code

    @app.route("/c2/v1", methods=["POST"])
    def postdata():

        try:
            # data = request.get_data()
            data = request.get_data()
            logging.info(f"post data goes like : {data[0:200]}")
            logging.debug(f"post data in json : {json.loads(data)}")

            # Asynchronously produce a message, the delivery report callback
            # will be triggered from poll() above, or flush() below, when the message has
            # been successfully delivered or failed permanently.

            received_data = json.loads(data)

            if "data" in received_data.keys():
                # received measurement type data
                key = received_data["n"]
            elif "ref" in received_data.keys():
                # received alarm or event type data
                key = received_data["n"]

            producer.send(
                topic="test.sputhan",
                key="",
                value=request.get_json(),
            )

            return success_response_object, success_code

        except Exception as e:
            producer.flush()
            logging.error("post data error", exc_info=True)
            # elastic_apm.capture_exception()
            return failure_response_object, failure_code

    return app
