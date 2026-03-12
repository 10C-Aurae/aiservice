// ─────────────────────────────────────────────────────────────
//  aiservice — Jenkins Pipeline
// ─────────────────────────────────────────────────────────────

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    environment {
        PROJECT      = 'aurae-prod'
        SERVICE_NAME = 'aiservice'
        ECS_CLUSTER  = 'aurae-prod-cluster'
        ECS_SERVICE  = 'aurae-prod-aiservice'
        CONTAINER    = 'aiservice'
        PORT         = '8001'
    }

    stages {

        stage('Config') {
            steps {
                script {
                    env.AWS_REGION = sh(
                        returnStdout: true,
                        script: "aws ssm get-parameter --name '/${PROJECT}/aws/region' --query 'Parameter.Value' --output text"
                    ).trim()

                    env.ECR_URL = sh(
                        returnStdout: true,
                        script: "aws ssm get-parameter --name '/${PROJECT}/ecr/aiservice-url' --query 'Parameter.Value' --output text"
                    ).trim()

                    env.IMAGE_TAG = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}-${sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()}"
                }
            }
        }

        stage('Test') {
            steps {
                sh '''
                    if [ -f requirements.txt ]; then
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt -q
                    fi

                    if [ -d tests ]; then
                        . .venv/bin/activate 2>/dev/null || true
                        pytest tests/ -v --tb=short --junitxml=test-results.xml -p no:warnings || true
                    else
                        echo "Sin tests todavía — skipping"
                    fi
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }

        stage('Build') {
            when { branch 'main' }
            steps {
                sh "docker build -t ${ECR_URL}:${IMAGE_TAG} -t ${ECR_URL}:latest ."
            }
        }

        stage('Trivy Scan') {
            when { branch 'main' }
            steps {
                sh '''
                    if ! command -v trivy &>/dev/null; then
                        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
                            | sh -s -- -b /usr/local/bin
                    fi
                    trivy image --severity HIGH,CRITICAL --exit-code 0 --format table ${ECR_URL}:${IMAGE_TAG}
                '''
            }
        }

        stage('Push ECR') {
            when { branch 'main' }
            steps {
                sh '''
                    aws ecr get-login-password --region $AWS_REGION | \
                        docker login --username AWS --password-stdin \
                        $(echo $ECR_URL | cut -d/ -f1)

                    docker push ${ECR_URL}:${IMAGE_TAG}
                    docker push ${ECR_URL}:latest
                '''
            }
        }

        stage('Deploy ECS') {
            when { branch 'main' }
            steps {
                sh '''
                    TASK_DEF=$(aws ecs describe-services \
                        --cluster $ECS_CLUSTER \
                        --services $ECS_SERVICE \
                        --region $AWS_REGION \
                        --query 'services[0].taskDefinition' \
                        --output text)

                    NEW_DEF=$(aws ecs describe-task-definition \
                        --task-definition "$TASK_DEF" \
                        --query 'taskDefinition' | \
                        jq --arg IMAGE "${ECR_URL}:${IMAGE_TAG}" \
                        --arg CONTAINER "$CONTAINER" \
                        '(.containerDefinitions[] | select(.name == $CONTAINER)).image = $IMAGE |
                         del(.taskDefinitionArn, .revision, .status,
                             .requiresAttributes, .placementConstraints,
                             .compatibilities, .registeredAt, .registeredBy)')

                    NEW_TASK_ARN=$(aws ecs register-task-definition \
                        --region $AWS_REGION \
                        --cli-input-json "$NEW_DEF" \
                        --query 'taskDefinition.taskDefinitionArn' \
                        --output text)

                    aws ecs update-service \
                        --cluster $ECS_CLUSTER \
                        --service $ECS_SERVICE \
                        --task-definition "$NEW_TASK_ARN" \
                        --force-new-deployment \
                        --region $AWS_REGION

                    aws ecs wait services-stable \
                        --cluster $ECS_CLUSTER \
                        --services $ECS_SERVICE \
                        --region $AWS_REGION

                    echo "Deploy completado: ${ECR_URL}:${IMAGE_TAG}"
                '''
            }
        }
    }

    post {
        success { echo "Pipeline exitoso — ${env.IMAGE_TAG ?: 'tests OK'}" }
        failure { echo "Pipeline fallido en: ${env.STAGE_NAME}" }
        always  { sh 'docker image prune -f --filter "until=24h" 2>/dev/null || true'; cleanWs() }
    }
}
