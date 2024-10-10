import argparse

from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

# Set up argument parsing
parser = argparse.ArgumentParser(description="Delete an Azure OpenAI deployment.")
parser.add_argument("--resource-name", required=True, help="The name of the Azure OpenAI resource.")
parser.add_argument("--resource-group", required=True, help="The name of the Azure resource group.")
parser.add_argument("--deployment-name", required=True, help="The name of the deployment to delete.")
parser.add_argument("--subscription-id", required=True, help="The Azure subscription ID.")

args = parser.parse_args()

# Authenticate using DefaultAzureCredential
credential = DefaultAzureCredential()

# Initialize the Cognitive Services client
client = CognitiveServicesManagementClient(credential, subscription_id=args.subscription_id)

# Begin delete the deployment
poller = client.deployments.begin_delete(
    resource_group_name=args.resource_group, account_name=args.resource_name, deployment_name=args.deployment_name
)

# Wait for the delete operation to complete
poller.result()

print(f"Deployment {args.deployment_name} deleted successfully.")
