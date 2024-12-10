pipeline {
    agent any
    environment {
        POETRY_HOME = "${WORKSPACE}/.poetry"
        PATH = "${WORKSPACE}/.poetry/bin:${PATH}"
        POETRY_CACHE_DIR = "${WORKSPACE}/.cache/pypoetry"
        POETRY_VIRTUALENVS_IN_PROJECT = "true"
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
//         stage('Install Poetry') {
//             steps {
//                 sh '''
//                 curl -sSL https://install.python-poetry.org | python3 -
//                 '''
//             }
//         }
        stage('Install Dependencies') {
            steps {
                sh '''
                poetry install
                '''
            }
        }
        stage('Run Tests') {
            steps {
                sh '''
                poetry run pytest
                '''
            }
        }
    }
}