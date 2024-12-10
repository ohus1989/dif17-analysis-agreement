pipeline {
    agent any
    environment {
        POETRY_HOME = "${WORKSPACE}/.poetry"
        PATH = "${WORKSPACE}/.poetry/bin:${PATH}"
        POETRY_CACHE_DIR = "${WORKSPACE}/.cache/pypoetry"
        POETRY_VIRTUALENVS_IN_PROJECT = "true"
        SRC = "/var/lib/jenkins/workspace/dif17-analysis-agreement-pipeline"
        DEST = "/opt/"
        INSTALL_SRC = "/opt/dif17-analysis-agreement"
    }
    stages {
        stage('Check and Install Poetry') {
            steps {
                sh '''
                if ! [ -x "$(command -v poetry)" ]; then
                    echo "Poetry not found. Installing..."
                    curl -sSL https://install.python-poetry.org | python3 -
                else
                    echo "Poetry already installed"
                    poetry --version
                fi
                '''
            }
        }
        stage('Remove .env File') {
            steps {
                sh '''
                if test -f "$SRC/.env"; then
                    echo "Removing existing .env file..."
                    rm "$SRC/.env"
                fi
                '''
            }
        }
        stage('Move Project Files') {
            steps {
                sh '''
                echo "Copying project files from $SRC to $DEST..."
                cp -rf "$SRC" "$DEST"
                '''
            }
        }
        stage('Install Dependencies') {
            steps {
                sh '''
                echo "Creating installation directory: $INSTALL_SRC"
                if ! mkdir -p "$INSTALL_SRC"; then
                    echo "Failed to create installation directory"
                    exit 1
                fi
                cd "$INSTALL_SRC"
                poetry install
                '''
            }
        }
// Uncomment this stage if you need to run tests
//         stage('Run Tests') {
//             steps {
//                 sh '''
//                 poetry run pytest
//                 '''
//             }
//         }
    }
}
