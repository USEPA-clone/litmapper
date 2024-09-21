# Deployment Scripts

The deployment is designed to run as follows:

1. Push to `deploy` branch in GitHub triggers Actions workflow `push_images`
2. Actions triggers an AWS SSM command which copies the new code to the production EC2 server and runs a shell script
3. Shell script runs on server and builds new images, pushes them to AWS ECR, recreates containers, and runs any new data loading steps.

The workflow requires the following to be set up manually:

1. Initial data placed at the expected location on the server (currently `/lit-mining/litmapper/etl/data`, see `scripts/load_data.sh` for more details)
2. Secrets set up in GitHub facilitating the deployment process - `AWS_ACCESS_KEY_ID` (AWS login key ID), `AWS_SECRET_ACCESS_KEY`(AWS login secret key), `AWS_DEFAULT_REGION` (matching the region of the EC2 instance), `AWS_EC2_INSTANCE_ID` (ID of the instance to deploy to)
3. AWS CLI (v2) installed on the EC2 server
4. Permissions set up for the IAM role associated with the EC2 server to access ECR
5. Secret set up in SSM providing a token for AWS to pull the repository (`ball-github-repo-pat`)
6. Elastic load balancer rules redirecting the following:

- `http://<ELB_URL>/literature-map` to `<EC2_IP>:8501`
- `http://<ELB_URL>/literature-map-static` to `<EC2_IP>:8502`
- `http://<ELB_URL>/drilldown` to `<EC2_IP>:8503`.

To check logs when deployment fails, browse to the AWS Systems Manager (SSM) section of the AWS web console.  Go to "Run Command" in the sidebar and check "Command history" (assuming the command already finished).  Select the most recent job, click the Command ID, and then click the Instance ID to go to the output for the passed instance.  Under Step 3 (the step that runs the remote shell script), click the "CloudWatch logs" link to see the full logs from the command.

There's a max 8 hour timeout for SSM jobs.  Running the data loading steps from scratch will exceed this and cause errors.  There are a few ways to deal with this:

1. The timed out job will complete but not create the checkpoint file that tells the `load_data.sh` script it doesn't need to rerun the step in the future.  Log on to the server and manually create this file (check `scripts/load_data.sh` to see where to create the file) to mark completion of that step.  This is easiest if there's only one or two steps to run, since you'll need to run the pipeline again and repeat this process if there are multiple steps timing out.
2. Manually run the `load_data.sh` script on the server.  Running it outside of SSM avoids the timeout.
3. Restore the server database from a backup taken from a database which has completed the data load.  You then **MUST** create all the checkpoint files expected by `scripts/load_data.sh` to avoid loading data again when the next deployment job runs.

## Local testing

You can use [act](https://github.com/nektos/act) to test the GitHub deployment workflow locally. Note the Docker image used for this is extremely large (~18GB).

To run the workflow, you must set the following environment variables:

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `AWS_EC2_INSTANCE_ID`: User must export these environment variables to authenticate to AWS.  Use the region associated with the EC2 instance.

Then run `scripts/ci/run_deploy.sh`.  This will deploy the current `deploy` branch to the EC2 server.

## File listing

- `deploy_push.json`: GitHub event file describing a push to the `deploy` branch, used for testing deployment locally.
- `login_ecr.sh`: Script to log into AWS ECR for accessing the Docker registry there.  AWS credentials must be configured (ex. environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).  The region is currently hard-coded, since it's different from the EC2 server region.
- `run_deploy.sh`: Script wrapping `act` which triggers the GitHub Actions deployment workflow from a local machine.
- `setup_server.sh`: Script which is run on the EC2 server to perform all deployment tasks, including building/pushing images, recreating app services, and loading data.  AWS credentials must be configured (ex. environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
