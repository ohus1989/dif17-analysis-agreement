pipeline {
    agent any
    environment {
        POETRY_HOME = "${WORKSPACE}/.poetry"
        PATH = "${WORKSPACE}/.poetry/bin:${PATH}"
        POETRY_CACHE_DIR = "${WORKSPACE}/.cache/pypoetry"
        POETRY_VIRTUALENVS_IN_PROJECT = "true"
        SRC=/var/lib/jenkins/workspace/dif17-analysis-agreement
        DEST=/opt/
        INSTALL_SRC=/opt/dif17-analysis-agreement
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
        stage('env 파일 지우기') {
            steps {
                sh '''
                if test -f "$SRC/.env"; then
                    rm $SRC/.env
                fi
                '''
            }
        }
        stage('프로젝트 파일 이동') {
            steps {
                sh '''
                cp -rf  $SRC $DEST
                '''
            }
        }
        stage('Install Dependencies') {
            steps {
                sh '''
                if ! mkdir -p $INSTALL_SRC; then
                    echo "Failed to create config directory"
                    exit 1
                fi
                cd $INSTALL_SRC
                poetry install --no-root
                '''
            }
        }
//         stage('Run Tests') {
//             steps {
//                 sh '''
//                 poetry run pytest
//                 '''
//             }
//         }
    }
}