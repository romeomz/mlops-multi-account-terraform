# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""A CLI to create or update and run pipelines."""
from __future__ import absolute_import

import argparse
import json
import sys
import traceback
import time

from pipelines._utils import (
    get_pipeline_driver,
    convert_struct,
    get_pipeline_custom_tags,
)


def main():
    """The main harness that creates or updates and runs the pipeline.
    Creates or updates the pipeline and runs it.
    """
    parser = argparse.ArgumentParser(
        "Creates or updates and runs the pipeline for the pipeline script."
    )

    parser.add_argument(
        "-n",
        "--module-name",
        dest="module_name",
        type=str,
        help="The module name of the pipeline to import.",
    )
    parser.add_argument(
        "-kwargs",
        "--kwargs",
        dest="kwargs",
        default=None,
        help="Dict string of keyword arguments for the pipeline generation (if supported)",
    )
    parser.add_argument(
        "-role-arn",
        "--role-arn",
        dest="role_arn",
        type=str,
        help="The role arn for the pipeline service execution role.",
    )
    parser.add_argument(
        "-description",
        "--description",
        dest="description",
        type=str,
        default=None,
        help="The description of the pipeline.",
    )
    parser.add_argument(
        "-tags",
        "--tags",
        dest="tags",
        default=None,
        help="""List of dict strings of '[{"Key": "string", "Value": "string"}, ..]'""",
    )
    args = parser.parse_args()

    if args.module_name is None or args.role_arn is None:
        parser.print_help()
        sys.exit(2)
    tags = convert_struct(args.tags)

    try:
        pipeline = get_pipeline_driver(args.module_name, args.kwargs)
        print(
            "###### Creating/updating a SageMaker Pipeline with the following definition:"
        )
        parsed = json.loads(pipeline.definition())
        print(json.dumps(parsed, indent=2, sort_keys=True))

        all_tags = get_pipeline_custom_tags(args.module_name, args.kwargs, tags)

        upsert_response = pipeline.upsert(
            role_arn=args.role_arn, description=args.description, tags=all_tags
        )
        print("\n###### Created/Updated SageMaker Pipeline: Response received:")
        print(upsert_response)

        execution = pipeline.start()
        print(f"\n###### Execution started with PipelineExecutionArn: {execution.arn}")
        pipeline_current_status = execution.describe()
        # print(job_description)
        print(f"\n###### Pipeline status is {pipeline_current_status['PipelineExecutionStatus']}")
        print("Waiting for the execution to finish...")

        # Setting the attempts and delay (in seconds) will modify the overall time the pipeline waits.
        # If the execution is taking a longer time, update these parameters to a larger value.
        # Eg: The total wait time is calculated as 60 * 120 = 7200 seconds (2 hours)
        # execution.wait(max_attempts=120, delay=60)
        # Loop until job is completed
        waited = 0
        timeout_minutes = 120
        while pipeline_current_status['PipelineExecutionStatus'] not in ['Succeeded', 'Failed']:
            time.sleep(60)
            waited += 60
            assert waited//60 < timeout_minutes, "Job timed out after %d seconds." % waited
            pipeline_current_status = execution.describe()
            if pipeline_current_status['PipelineExecutionStatus'] == 'Stopped':
                print("\n#####Execution Stopped...")
                break

        print("\n#####Execution step details:")
        print(execution.list_steps())
        print(f"\n###### Pipeline status is {execution.describe()['PipelineExecutionStatus']}")
        if execution.describe()['PipelineExecutionStatus'] == 'Succeeded':
            return 0
        else:
            return 1
    except Exception as e:  # pylint: disable=W0703
        print(f"Exception: {e}")
        traceback.print_exc()
        sys.exit(1)


def main_target(module_name, kwargs, description=''):
    try:
        pipeline = get_pipeline_driver(module_name, kwargs)
        print(
            "###### Creating/updating a SageMaker Pipeline with the following definition:"
        )
        parsed = json.loads(pipeline.definition())
        print(json.dumps(parsed, indent=2, sort_keys=True))

        return pipeline.definition()
    except Exception as e:  # pylint: disable=W0703
        print(f"Exception: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # main()
    sys.exit(main())
