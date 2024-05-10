// activities for productcatalogservice microservices starts

        stage('productcatalogservice || 09') {
            parallel {
                stage('OWASP SBOM/ Dependency Check(productcatalogservice)') {
                    when {
                        changeset "**/productcatalogservice/**"
                    }
                    steps {
                        dir('onlineboutique') {
                            script {
                            // Create a directory for the reports with permission 777
                            def reportsDir = "${env.WORKSPACE}/onlineboutique/sbom-dependency-check-reports/productcatalogservice-sbom"
                            sh "mkdir -m 777 -p ${reportsDir}"
                            sh "touch productcatalogservice-sbom-DUMMY"
                            sh "mv productcatalogservice-sbom-* ${reportsDir}/"
                            sh "rm -rf ${reportsDir}/productcatalogservice-sbom-DUMMY"
                        
                            // Perform OWASP Dependency-Check scan
                            def currentDateTime = new Date().format('yyyy-MM-dd_HH-mm-ss')
                            def sbomFileName = "productcatalogservice-sbom-${currentDateTime}.html"
                            def sbomFilePath = "${env.WORKSPACE}/onlineboutique/${sbomFileName}"
                            dependencyCheck(additionalArguments: "--scan **/src/productcatalogservice/go.mod -f HTML -o ${sbomFilePath}", odcInstallation: 'DC')
			    // src/productcatalogservice/go.mod
                                }
                            }
                        }
                    }
                
                
                stage('productcatalogservice build') {
                     when {
                        changeset "**/productcatalogservice/**"
                    }
                    steps {
                        dir('onlineboutique/src/productcatalogservice/') {
                            script {
                                withDockerRegistry(credentialsId: 'docker-cred', toolName: 'docker') {
                                // dir('/var/lib/jenkins/workspace/CMU-CAPSTONE-G5P7/onlineboutique/src/productcatalogservice/') {
                                    // Build the Docker image

                                    sh "docker build -t cmupro7/productcatalogservice:${BUILD_NUMBER} ."
                                    // Push the Docker image to Docker Hub
                                    sh "docker push cmupro7/productcatalogservice:${BUILD_NUMBER}"
                                    // Remove the local Docker image
                                    sh "docker rmi cmupro7/productcatalogservice:${BUILD_NUMBER}"
                                }
                            }   
                        }
                    }
                }
            
        } // parellel
    }  // stage 09
    
   stage('productcatalogservice - K8s Manifest Update/CD') {
     when {
            changeset "**/productcatalogservice/**"
        }
    environment {
        GIT_REPO_NAME = "cmu-artifacts"
        GIT_USER_NAME = "b4shailen"
    }
    steps {
        dir('cmu-artifacts') {
            script {
                def pattern = "image: cmupro7/productcatalogservice:[0-9]{1,5}"
                def replacement = "image: cmupro7/productcatalogservice:${BUILD_NUMBER}"
                def yamlFile = "Deploy/manifests/productcatalogservice_rollout.yaml"
                
                // Read the contents of the YAML file
                def yamlContent = readFile(yamlFile)
                
                // Replace the pattern with the BUILD_NUMBER
                def updatedContent = yamlContent.replaceAll(pattern, replacement)
                
                // Write the updated content back to the file
                writeFile file: yamlFile, text: updatedContent
                
                // Add, commit, and push the changes to the Git repository
                withCredentials([string(credentialsId: 'github1', variable: 'GITHUB_TOKEN')]) {
                    sh '''
                        git config user.email "b4shailen@gmail.com"
                        git config user.name "Shailendra Singh"
                        git add Deploy/manifests/productcatalogservice_rollout.yaml
                        git commit -m "Update deployment image to version ${BUILD_NUMBER}"
                        git push https://${GITHUB_TOKEN}@github.com/${GIT_USER_NAME}/${GIT_REPO_NAME} HEAD:main
                    '''
                }
            }
        }
    }
}

// activities for productcatalogservice microservices ends.
