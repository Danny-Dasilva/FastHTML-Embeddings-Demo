pip install git+https://github.com/openai/CLIP.git

docker network create pgvectorscale-network



docker run -d --name timescaledb --network pgvectorscale-network -p 5432:5434 -e POSTGRES_PASSWORD=password timescale/timescaledb-ha:pg16
docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb-ha:pg16


docker build -t my-python-app .

docker run -d --network pgvectorscale-network -p 5001:5001 my-python-app