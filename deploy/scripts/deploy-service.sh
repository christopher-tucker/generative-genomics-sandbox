#!/bin/bash
set -e

# Load infrastructure configuration
source deploy/scripts/infrastructure-config.sh

echo "Deploying Generative Genomics service to ECS..."

# 1. Register task definition
echo "Registering ECS task definition..."
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://deploy/ecs/task-definition.json \
    --query "taskDefinition.taskDefinitionArn" \
    --output text \
    --region $REGION)

echo "Task definition registered: $TASK_DEF_ARN"

# 2. Create or update ECS service
echo "Creating/updating ECS service..."

# Check if service exists
if aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query "services[0].serviceName" \
    --output text 2>/dev/null | grep -q $SERVICE_NAME; then
    
    echo "Service exists, updating..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_DEF_ARN \
        --region $REGION
else
    echo "Creating new service..."
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_DEF_ARN \
        --desired-count 1 \
        --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
        --network-configuration "awsvpcConfiguration={subnets=[$(echo $SUBNET_IDS | tr ' ' ',')],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=generative-genomics-app,containerPort=8080 \
        --health-check-grace-period-seconds 300 \
        --region $REGION
fi

echo ""
echo "✅ Deployment initiated!"
echo ""
echo "🔍 Monitor deployment:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo ""
echo "📋 View logs:"
echo "aws logs tail /ecs/generative-genomics-demo --follow --region $REGION"
echo ""
echo "🌐 Your app will be available at: http://$ALB_DNS"
echo ""
echo "⏱️  Deployment typically takes 3-5 minutes..."