def paymentservice() {
        stage('Hello Paymentservice!') {
            steps {
                echo "Step: Executing paymentservicePipeline() method..."
            }
        } // stage
       
        stage('Deploy Paymentservice') {
            echo "deployment Paymentservice steps"
          }
          // ... add other stages as needed
} // def activities for paymentservice microservices ends.
