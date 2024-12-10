pipeline {
    agent any
    environment {
        POETRY_HOME = "${WORKSPACE}/.poetry"
        PATH = "${WORKSPACE}/.poetry/bin:${PATH}"
        POETRY_CACHE_DIR = "${WORKSPACE}/.cache/pypoetry"
        POETRY_VIRTUALENVS_IN_PROJECT = "true"
        SRC = "/var/lib/jenkins/workspace/dif17-analysis-agreement"
        DEST = "/opt/"
        INSTALL_SRC = "/opt/dif17-analysis-agreement"
        PORT=8003
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

                # Test uvicorn command directly
                echo "Testing uvicorn command..."
                poetry run uvicorn main:app --reload --port=$PORT || echo "Direct uvicorn test failed"

                # Start the uvicorn server with nohup
                echo "Starting server with nohup..."
                nohup poetry run uvicorn main:app --reload --port=$PORT > $INSTALL_SRC/nohup.out 2>&1 &
                SERVER_PID=$!

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
    }
}
