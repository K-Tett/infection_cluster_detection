# Infection Cluster Detection

## Brief
Python-based service to automate the detection of infection cluster in a hospital setting. 

## How?
It ingests patient movement records and microbiology test results to identify groups of related cases, and to provide insights to infection prevention and control teams.

### What is a Cluster?
A cluster is a group of related cases that may indicate a common exposure or outbreak. These clusters often emerge from contact tracing data, where patients are linked through shared locations (e.g., wards, theatres) or overlapping stays.

## Key goals:
- Demonstrate clean, efficient code.
- Handle edge cases and optimize where possible.
- Provide clear documentation for easy review.

## Prerequisites
- Python 3.10+
- Node.js 24+
- PostgreSQL 17.x+
- Docker 28.x.x+ for containerized runs, if applicable

### Tools used
- Pandas (Data Parse)
- NetworkX (Cluster)
- sqlalchemy (SQL)
- D3.js (Graph nodes and links)

## Tech Stack
- Frontend: Angular (TS)
- Backend: Python (FastAPI)
- Database: PostgreSQL
- Containerization: Docker
- LLM: ```huggingface``` using ```microsoft/Phi-4-multimodal-instruct``` (fit for 16gb VRAM GPU)

## Project Structure
``` md
.
├── data/
│   ├── transfers.csv
│   └── microbiology.csv
├── backend/
│   ├── main.py
│   ├── init.py
│   └── services/
│       └── cluster_detection.py
├── src/
│   └── app/
│       └── # .css,.ts,.html files
├── tests/
│   └── # unit test files
├── README.md
├── requirements.txt
└── docker-compose.yml
```

## File Structure
#### ```transfers.csv``` columns:
-  transfer\_id (string) : primary key, unique transfer identifier. 
-  patient\_id (string) : Foring key, unique patient identifier 
- ward\_in\_time (date) : date of admission to ward 
- ward\_out\_time (date) : date of discharge from ward 
- location (string) : the location of the patient 

#### ```microbiology.csv``` columns: 
- test\_id (string) : primary key, unique test 
- patient\_id (string) : foreign key linking to a unique patient identifier ● collection\_date (date) : the date on which the test was taken on 
- infection (string) : i.e. the infection type being tested for  
- result (string) : ‘positive’ or ‘negative’ based on whether the infection was identified 

## Setup
1. Install dependencies:
``` bash
    pip install -r requirements.txt
```
``` bash
    npm install
```
2. Run the docker container to start PostgreSQL.
```bash
    # if on Windows, ensure to run WSL first then open Docker Desktop
    .\start.bat
```
3. Run the setup for the backend first
```bash
    python setup_db.py
```
4. Run the FastAPI server (Backend only)[^1]:
``` bash
    # move to backend dir
    cd .\backend
    # start the backend service
    uvicorn main:app --reload
``` 
5. Run the frontend [^2]:
``` bash
    # move back to src
    cd ..
    # run Angular dev server
    ng serve
```

[^1] The application will be running at http://127.0.0.1:8000.
[^2] The platform will be running at

## Features 
### Upload Files
* URL: /upload/
* Method: POST
* Description: Uploads transfers.csv and microbiology.csv files.
* Form data:
    * files: Select the two CSV files.

### Detect Clusters
* URL: /clusters/
* Method: GET
* Description: Identifies and returns infection clusters from the uploaded data.
* Response: A JSON object containing the detected clusters.

### LLM Summarizer
* LLM has not being implemented
* Use 5 sets of mock responses
```typescript
    switch (filterType) {
      case 'cluster_id':
        response = `Cluster ${cluster.id} contains ${cluster.patientCount} patients with ${cluster.infection} infection. This cluster represents a significant outbreak requiring immediate attention and isolation protocols.`;
        break;
      case 'size':
        response = `This ${cluster.infection} cluster involves ${cluster.patientCount} patients. ${cluster.patientCount > 5 ? 'Large cluster size indicates high transmission risk.' : 'Moderate cluster size suggests contained transmission.'}`;
        break;
      case 'location':
        response = `${cluster.infection} cluster detected across multiple ward locations. Geographic spread suggests possible nosocomial transmission requiring enhanced infection control measures.`;
        break;
      case 'timeframe':
        response = `${cluster.infection} cluster timeframe spans multiple days with overlapping patient stays. Temporal clustering indicates active transmission period requiring immediate intervention.`;
        break;
      case 'significance':
        response = `High significance cluster: ${cluster.patientCount} patients with ${cluster.infection}. Recommend immediate isolation, contact tracing, and enhanced cleaning protocols.`;
        break;
    }
```

# Angular CLI commands
## Development server
To start a local development server, run:
```bash
ng serve
```
Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding
Angular CLI includes powerful code scaffolding tools. To generate a new component, run:
```bash
ng generate component component-name
```
For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:
```bash
ng generate --help
```

## Building
To build the project run:
```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests
To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:
```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Design Decisions and Trade-offs
### Why this design choice?
- Graph nodes are color-coded to indicate the contact window.
- Spatial clustering is easy to understand which capture basic link.
- Postgres server to provide ACID compliance for medical data.

### Trade off
- Direct contact cluster is simplified approach and couldn't indicate how each individual interact with each other, directly or indirectly.
- Pathogens can travel either airborne or need direct contact, which this cluster method didn't show how significant the location is.
- Non-patient may be the patient-zero.
- Currently, the risk factor is calculated with how many connections a patient has contacted with in the time window.
- Direction of infection: We don't know who spread infection to whom?
- It needs to compare with every other patient which increase the computation complexity.
- Missing link to the equation would break the clustering and causes us to mistake two different clusters to be low risk or significance.
- REST endpoints is fast for small request, but larger dataset upload or request will timeout the system.
    - Celery with Redis could be a next step
- Currently, we save everything in memory to show the data on table, list and the graph. It is not efficient when scale up.

# Roadmap
- [ ] StEP model: add proximity model instead of direct contact to form a cluster
- [ ] Improve algorithm: add how many days has the person contact to specific group of patients and color code them to show how much risk they are in. We can create a risk dictionary for each location if smaller area, then the chance of contact is higher than a wide space.
- [ ] Hierarchical Density-Based Spatial Clustering of Applications with Noise (HDBSCAN): use numpy to clusters data points or 'hotspot' into clusters of varying shapes and sizes and automatically ignoring outliers, by building a hierarchy of dense regions and extracting the most stable clusters.
- [ ] A greedy algorithm with Louvain method: provide the graph maximum density of high-weight links in a cluster and minimize the links with other clusters. This will ignore false postive links.
- [ ] Analyze before clustering: identify source or patient zero and trace the link as the patient zero will be the most crucial point of outbreak and most risky to spread further. 
- [ ] Interactive timeline and curve like CATHAI
- [ ] Early warning system based on the use of anitbiotircs (Fan et al. paper)
- [ ] GraphRAG: add guidelines or related documents to formulate the best course of actions for clinician if we found a big or small cluster of potential infection.
- [ ] LLM API: GPT-5 nano from OpenAI or Gemini 2.5 Flash from Google as first line LLM before fall back to local LLM and fallback to mock response.
- [ ] LLM analyzer improvement: highlights clusters when providing an answer to the prompt
- [ ] Parquet file conversion
- [ ] LLM analyzer: add the LLM analyzer on the sidebar with working LLM
- [ ] UXUI improvements: circle around the cluster to identify the clusters ID when zoom out. group the clusters that is high risk or low risk in their own bigger circles. Histogram and timeline to show the contact events over time.
- [ ] Proper DevOps implementation: run frontend, backend and database in containers.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.