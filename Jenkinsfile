pipeline {
    agent any

    parameters {
        stashedFile name: 'exchcomp.csv',
            description: 'The CSV containing the list of companies in the desired stock exchange.'
        string name: 'exchange',
            description: 'A shorthand name to prepend to all artifacts. Should contain the stock exchange name.'
        string name: 'exchanges',
            description: 'A comma-separated list of the Yahoo Finance exchanges to look for a stock (e.g., EPA,BR,AS)'
        string name: 'title',
            description: 'The title for this build'
    }

    environment{
        now = (new Date()).format("yyyy-MM-dd")
    }

    stages {
        stage('Checkout GitHub Repo') {
            steps {
                script {
                    // The below will clone your repo and will be checked out to master branch by default.
                    git credentialsId: 'ssh-github', url: 'git@github.com:michalismeng/dividend-search.git'
                    // Do a ls -lart to view all the files are cloned. It will be clonned. This is just for you to be sure about it.
                    sh "ls -lart ./*"
                    sh "mkdir -p _data"
                    if (title != null){
                        currentBuild.displayName = "${title}"
                    }
                } 
            }
        }
        stage('Perform Scratch Search') {
            steps {
                unstash 'exchcomp.csv'
                sh """
                    python3 -m venv python_venv
                    . python_venv/bin/activate
                    python3 -m pip install -r requirements.txt
                    python3 -u scratch.py -e $exchanges -f exchcomp.csv -o _data/${exchange}-dividend-data-${now}.csv
                    cat exchcomp.csv > _data/${exchange}-listed-companies.csv
                    deactivate
                """
            }
        }
        stage('Filter Data') {
            steps {
                sh """
                    python3 -m venv python_venv
                    . python_venv/bin/activate
                    python3 -m pip install -r requirements.txt
                    python3 -u read_data.py _data/${exchange}-dividend-data-${now}.csv --no-filter | tee _data/${exchange}-dividend-data-unfiltered-${now}.html
                    python3 -u read_data.py _data/${exchange}-dividend-data-${now}.csv | tee _data/${exchange}-dividend-data-filtered-${now}.html
                    deactivate
                """
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '_data/*.csv, _data/*.html', fingerprint: true
            cleanWs()
        }
    }
}