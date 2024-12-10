pipeline {
    agent any
    environment {
        POETRY_HOME = "${WORKSPACE}/.poetry"
        PATH = "${WORKSPACE}/.poetry/bin:${PATH}"
        POETRY_CACHE_DIR = "${WORKSPACE}/.cache/pypoetry"
        POETRY_VIRTUALENVS_IN_PROJECT = "true"
        PROJECT_NAME="dif17-analysis-agreement"
        SRC = "/var/lib/jenkins/workspace/${PROJECT_NAME}"
        DEST = "/opt/"
        INSTALL_SRC = "/opt/${PROJECT_NAME}"
        PORT=8003
        SERVER_PID_FILE = "/opt/${PROJECT_NAME}/server.pid"
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
        stage('기존 실행 프로젝트 킬') {
            steps {
                sh '''
                echo "Killing existing dif17-analysis-agreement processes..."
                # Kill all related processes
                ps -aux | grep /opt/dif17-analysis-agreement
                PROCESSES=$(ps -aux | grep /opt/dif17-analysis-agreement | grep -v grep | awk '{ print $2 }')
                if [ -n "$PROCESSES" ]; then
                    echo "Found processes: $PROCESSES"
                    sudo kill -9 $PROCESSES || echo "Failed to kill some processes"
                else
                    echo "No matching processes found"
                fi

                # Kill inotifywait process if exists
                if pgrep inotifywait > /dev/null; then
                    echo "Killing inotifywait process"
                    sudo killall inotifywait || echo "Failed to kill inotifywait process"
                else
                    echo "No inotifywait process found"
                fi
                '''
            }
        }
        stage('프로젝트 실행') {
            steps {
                sh '''
                echo "Starting dif17-analysis-agreement project..."

                DIR=$PWD
                echo "Current working directory: $DIR"

                if ! cd $INSTALL_SRC; then
                    echo "Failed to change directory to $INSTALL_SRC"
                    exit 1
                fi
                echo "Changed directory to: $PWD"

                # Start the uvicorn server with nohup
                # 프로세스를 Jenkins로부터 분리
                JENKINS_NODE_COOKIE=dontKillMe nohup poetry run uvicorn main:app --reload --port=$PORT > $INSTALL_SRC/nohup.out 2>&1 &

                # PID 저장
                echo $! > $SERVER_PID_FILE
                SERVER_PID=$(cat $SERVER_PID_FILE)

                echo "Uvicorn server started with PID $SERVER_PID"

                # Verify that the server started successfully
                sleep 5
                if ps -p $SERVER_PID > /dev/null; then
                    echo "Uvicorn server started successfully with PID $SERVER_PID"
                else
                    echo "Failed to start uvicorn server"
                    cat $INSTALL_SRC/nohup.out
                    exit 1
                fi
                '''
            }
        }
        stage('서버 상태 확인') {
            steps {
                sh '''
                # 저장된 PID로 서버 상태 확인
                if [ -f $SERVER_PID_FILE ]; then
                    SERVER_PID=$(cat $SERVER_PID_FILE)
                    if ps -p $SERVER_PID > /dev/null; then
                        echo "Uvicorn server is running with PID $SERVER_PID"
                    else
                        echo "Uvicorn server is not running"
                        exit 1
                    fi
                else
                    echo "Server PID file not found"
                    exit 1
                fi
                '''
            }
        }
    }
}
