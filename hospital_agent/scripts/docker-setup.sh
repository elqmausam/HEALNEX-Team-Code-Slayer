#!/bin/bash
# scripts/docker-setup.sh
# Quick Docker setup and management script

set -e

echo "============================================"
echo "🐳 Hospital Agent - Docker Setup"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        echo "Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_status "Docker is installed"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        echo "Install from: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_status "Docker Compose is installed"
}

# Check .env file
check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found!"
        echo "Creating from .env.example..."
        cp .env.example .env
        print_status ".env file created"
        print_warning "IMPORTANT: Edit .env and add your API keys!"
        echo "Required: GEMINI_API_KEY, PINECONE_API_KEY, JWT_SECRET_KEY"
    else
        print_status ".env file exists"
    fi
}

# Create required directories
create_directories() {
    echo ""
    echo "Creating required directories..."
    mkdir -p logs data scripts
    touch logs/.gitkeep data/.gitkeep
    print_status "Directories created"
}

# Build Docker images
build_images() {
    echo ""
    echo "Building Docker images..."
    docker-compose build --no-cache
    print_status "Images built successfully"
}

# Start services
start_services() {
    echo ""
    echo "Starting services..."
    docker-compose up -d
    print_status "Services started"
}

# Check service health
check_health() {
    echo ""
    echo "Checking service health..."
    sleep 5
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        print_status "Redis is healthy"
    else
        print_error "Redis health check failed"
    fi
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres | grep -q "accepting connections"; then
        print_status "PostgreSQL is healthy"
    else
        print_error "PostgreSQL health check failed"
    fi
    
    # Wait for app to be ready
    echo ""
    echo "Waiting for Hospital Agent to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Hospital Agent is healthy!"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    
    print_warning "Hospital Agent may not be fully ready yet"
}

# Show logs
show_logs() {
    echo ""
    echo "Recent logs:"
    docker-compose logs --tail=20 hospital-agent
}

# Display URLs
show_urls() {
    echo ""
    echo "============================================"
    echo "🎉 Setup Complete!"
    echo "============================================"
    echo ""
    echo "📡 Access Points:"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Health Check:      http://localhost:8000/health"
    echo "  • Redis:             localhost:6379"
    echo "  • PostgreSQL:        localhost:5432"
    echo ""
    echo "🧪 Test Commands:"
    echo "  • Health: curl http://localhost:8000/health"
    echo "  • Chat:   curl -X POST http://localhost:8000/api/v1/chat/message \\"
    echo "              -H 'Content-Type: application/json' \\"
    echo "              -d '{\"message\":\"Hello\",\"hospital_id\":\"H001\"}'"
    echo ""
    echo "📊 Optional Services (with profiles):"
    echo "  • Debug tools:    docker-compose --profile debug up -d"
    echo "  • Monitoring:     docker-compose --profile monitoring up -d"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • View logs:      docker-compose logs -f hospital-agent"
    echo "  • Restart:        docker-compose restart hospital-agent"
    echo "  • Stop all:       docker-compose down"
    echo "  • Clean all:      docker-compose down -v"
    echo ""
}

# Main execution
main() {
    echo ""
    check_docker
    check_docker_compose
    check_env
    create_directories
    
    echo ""
    read -p "Do you want to build and start services now? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
        start_services
        check_health
        show_logs
        show_urls
    else
        echo ""
        print_status "Setup complete! Run 'docker-compose up -d' when ready."
    fi
}

# Run main function
main


# ============================================
# scripts/init_db.sql
# PostgreSQL initialization script
# ============================================

-- Create database if not exists
SELECT 'CREATE DATABASE hospital_agent'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hospital_agent')\gexec

-- Connect to database
\c hospital_agent;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create tables
CREATE TABLE IF NOT EXISTS hospitals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    bed_capacity INTEGER,
    specialties JSONB,
    risk_tolerance VARCHAR(50),
    budget_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id VARCHAR(50) REFERENCES hospitals(hospital_id),
    forecast_days INTEGER NOT NULL,
    prediction_data JSONB NOT NULL,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hospital_id VARCHAR(50) REFERENCES hospitals(hospital_id),
    message TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_hospitals_hospital_id ON hospitals(hospital_id);
CREATE INDEX IF NOT EXISTS idx_predictions_hospital_id ON predictions(hospital_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_hospital_id ON conversations(hospital_id);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);

-- Insert sample hospital
INSERT INTO hospitals (hospital_id, name, location, bed_capacity, specialties, risk_tolerance, budget_level)
VALUES (
    'H001',
    'City General Hospital',
    'Mumbai',
    230,
    '["Emergency", "ICU", "General", "Maternity", "Pediatrics"]'::jsonb,
    'medium',
    'medium'
) ON CONFLICT (hospital_id) DO NOTHING;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger
DROP TRIGGER IF EXISTS update_hospitals_updated_at ON hospitals;
CREATE TRIGGER update_hospitals_updated_at
    BEFORE UPDATE ON hospitals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;


# ============================================
# scripts/docker-commands.sh
# Useful Docker commands
# ============================================

#!/bin/bash

echo "Hospital Agent Docker Commands"
echo "=============================="
echo ""
echo "🚀 Starting Services:"
echo "  docker-compose up -d                    # Start all services"
echo "  docker-compose up -d hospital-agent     # Start only main app"
echo "  docker-compose --profile debug up -d    # Start with debug tools"
echo ""
echo "🛑 Stopping Services:"
echo "  docker-compose stop                     # Stop all services"
echo "  docker-compose down                     # Stop and remove containers"
echo "  docker-compose down -v                  # Stop and remove volumes"
echo ""
echo "📊 Viewing Logs:"
echo "  docker-compose logs -f                  # Follow all logs"
echo "  docker-compose logs -f hospital-agent   # Follow app logs only"
echo "  docker-compose logs --tail=100          # Last 100 lines"
echo ""
echo "🔄 Restarting:"
echo "  docker-compose restart                  # Restart all"
echo "  docker-compose restart hospital-agent   # Restart app only"
echo ""
echo "🔍 Status & Health:"
echo "  docker-compose ps                       # Show running containers"
echo "  docker-compose top                      # Show processes"
echo "  curl http://localhost:8000/health       # Check app health"
echo ""
echo "🗄️ Database Commands:"
echo "  docker-compose exec postgres psql -U postgres -d hospital_agent"
echo "  docker-compose exec redis redis-cli"
echo ""
echo "🧹 Cleanup:"
echo "  docker-compose down --rmi all           # Remove images too"
echo "  docker system prune -a                  # Clean everything"
echo ""
echo "🔧 Rebuild:"
echo "  docker-compose build --no-cache         # Rebuild images"
echo "  docker-compose up -d --build            # Rebuild and start"
echo ""