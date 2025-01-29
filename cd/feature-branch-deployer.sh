#!/bin/bash

set -eo pipefail

required_tools=(
  gcloud
  jq
  kubectl
)
for tool in "${required_tools[@]}"; do
  if ! command -v "$tool" &> /ENVIRONMENT/null; then
    echo "Pre-deploy check failed: $tool could not be found"
    exit 1
  fi
done

required_env_vars=(
  NAMESPACE
  GCP_REGION
  GCP_PROJECT
  CLUSTER_NAME
  IMAGE_NAME
  SERVICE_NAME
  DEPLOYMENT_NAME
  DEPLOYMENT_FILE
  CONFIG_MAP_FILE
  CONFIG_MAP_NAME
  SERVICE_FILE
  GOOGLE_JSON_CREDENTIALS
  FEATURE_BRANCH_TAG
)
for var in "${required_env_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "Pre-deploy check failed: $var is not set"
    exit 2
  fi
done

echo "$GOOGLE_JSON_CREDENTIALS" | jq . > credentials.json
if ! gcloud auth activate-service-account --key-file credentials.json --project "${GCP_PROJECT}"; then
  echo "Failed to authenticate with GCP for project ${GCP_PROJECT}"
  exit 3
fi

echo "Retrieve GKE credentials from ${CLUSTER_NAME} in ${GCP_REGION} for project ${GCP_PROJECT}"
if ! gcloud container clusters get-credentials "${CLUSTER_NAME}" --region "${GCP_REGION}" --project "${GCP_PROJECT}"; then
  echo "Failed to retrieve GKE credentials..."
  exit 4
fi

export BACKEND_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${IMAGE_NAME}:${FEATURE_BRANCH_TAG}"
echo "Backend image: ${BACKEND_IMAGE}"

echo "Deleting existing deployment ${DEPLOYMENT_NAME} and service ${SERVICE_NAME}..."
kubectl delete configmap "$CONFIG_MAP_NAME" -n ENVIRONMENT --ignore-not-found=true -n "${NAMESPACE}"
kubectl delete deployment "$DEPLOYMENT_NAME" -n ENVIRONMENT --ignore-not-found=true -n "${NAMESPACE}"
kubectl get pods -n "${NAMESPACE}"
kubectl delete service "${SERVICE_NAME}" -n ENVIRONMENT --ignore-not-found=true -n "${NAMESPACE}"
kubectl get services -n "${NAMESPACE}"

echo "Deploying to ${NAMESPACE} using:"
echo "- ConfigMap file: ${CONFIG_MAP_FILE}"
echo "- Deployment file: ${DEPLOYMENT_FILE}"
echo "- Service file: ${SERVICE_FILE}"
echo "with substituted environment variables."

envsubst < "$CONFIG_MAP_FILE" | kubectl -n "${NAMESPACE}" apply -f -
envsubst < "$DEPLOYMENT_FILE" | kubectl -n "${NAMESPACE}" apply -f -
envsubst < "$SERVICE_FILE" | kubectl -n "${NAMESPACE}" apply -f -

echo "Deployment complete."
echo "REMINDER: Feature branch deployments are NOT automatically cleaned up, and are NOT health checked."
echo "          Also, you can only deploy one feature branch at a time, so be mindful of other user deployments."

exit 0