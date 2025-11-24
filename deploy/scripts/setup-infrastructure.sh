#!/bin/bash
set -e

REGION="us-west-2"
CLUSTER_NAME="generative-genomics-cluster"
SERVICE_NAME="generative-genomics-service"
ALB_NAME="generative-genomics-alb"

echo "Setting up AWS infrastructure for Generative Genomics Demo..."

# 1. Create ECS Cluster
echo "Creating ECS cluster..."
aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --capacity-providers FARGATE_SPOT FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
    --region $REGION

# 2. Create CloudWatch Log Group
echo "Creating CloudWatch log group..."
aws logs create-log-group \
    --log-group-name "/ecs/generative-genomics-demo" \
    --region $REGION 2>/dev/null || echo "Log group already exists"

aws logs put-retention-policy \
    --log-group-name "/ecs/generative-genomics-demo" \
    --retention-in-days 7 \
    --region $REGION 2>/dev/null || echo "Retention policy already set"

# 3. Create IAM roles if they don't exist
echo "Creating IAM roles..."

# Task Execution Role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "ecsTaskExecutionRole already exists"

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Task Role
aws iam create-role \
    --role-name ecsTaskRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "ecsTaskRole already exists"

# 4. Get default VPC and subnets
echo "Getting VPC information..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $REGION)
SUBNET_ARRAY=($SUBNET_IDS)

echo "Using VPC: $VPC_ID"
echo "Using subnets: ${SUBNET_ARRAY[@]}"

# 5. Create Security Groups
echo "Creating security groups..."

# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name generative-genomics-alb-sg \
    --description "Security group for Generative Genomics ALB" \
    --vpc-id $VPC_ID \
    --query "GroupId" \
    --output text \
    --region $REGION 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=generative-genomics-alb-sg" \
    --query "SecurityGroups[0].GroupId" \
    --output text \
    --region $REGION)

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || echo "ALB ingress rule already exists"

# ECS Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name generative-genomics-ecs-sg \
    --description "Security group for Generative Genomics ECS tasks" \
    --vpc-id $VPC_ID \
    --query "GroupId" \
    --output text \
    --region $REGION 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=generative-genomics-ecs-sg" \
    --query "SecurityGroups[0].GroupId" \
    --output text \
    --region $REGION)

aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8080 \
    --source-group $ALB_SG_ID \
    --region $REGION 2>/dev/null || echo "ECS ingress rule already exists"

# 6. Create Application Load Balancer
echo "Creating Application Load Balancer..."
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name $ALB_NAME \
    --subnets ${SUBNET_ARRAY[@]} \
    --security-groups $ALB_SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --query "LoadBalancers[0].LoadBalancerArn" \
    --output text \
    --region $REGION)

# 7. Create Target Group
echo "Creating target group..."
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name generative-genomics-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path "/api/health" \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text \
    --region $REGION)

# 8. Create ALB Listener
echo "Creating ALB listener..."
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $REGION

# 9. Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query "LoadBalancers[0].DNSName" \
    --output text \
    --region $REGION)

echo ""
echo "✅ Infrastructure setup complete!"
echo ""
echo "Resources created:"
echo "- ECS Cluster: $CLUSTER_NAME"
echo "- ALB: $ALB_NAME"
echo "- Target Group: generative-genomics-tg"
echo "- Security Groups: $ALB_SG_ID, $ECS_SG_ID"
echo ""
echo "🌐 Your app will be available at: http://$ALB_DNS"
echo ""
echo "Next step: Run ./deploy/scripts/deploy-service.sh to deploy your application"

# Save important values for deployment script
cat > deploy/scripts/infrastructure-config.sh << EOF
REGION="$REGION"
CLUSTER_NAME="$CLUSTER_NAME"
SERVICE_NAME="$SERVICE_NAME"
TARGET_GROUP_ARN="$TARGET_GROUP_ARN"
ECS_SG_ID="$ECS_SG_ID"
SUBNET_IDS="${SUBNET_ARRAY[*]}"
ALB_DNS="$ALB_DNS"
EOF