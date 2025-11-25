# Database Migration Demo: Postgres to MongoDB

A demonstration project showcasing migration from a relational database (Supabase/Postgres) to a document database (MongoDB) for a collaborative project management application.

## Project Overview

This demo simulates a real-world scenario where a client needs to migrate from Oracle DB (represented here by Supabase/Postgres) to MongoDB. The application is a "Trello/Jira-lite" project management system with:

- Multiple organizations
- Users belonging to multiple organizations
- Projects with tasks
- Tasks with comments, labels, and assignees

## Demo Objectives

1. **Explore** a fully normalized relational schema
2. **Design** an appropriate MongoDB document schema
3. **Build** ETL scripts to migrate data with proper transformations
4. **Validate** the migration results

## Project Structure

```
database-migration/
├── source/          # Supabase/Postgres source database (COMPLETE)
├── sink/            # MongoDB target database (INFRASTRUCTURE ONLY)
├── etl/             # ETL scripts (TO BE BUILT DURING DEMO)
└── docs/            # Best practices and demo guidelines
```

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Supabase account (free tier)
- Git

### Setup Instructions

1. **Clone and install dependencies**
   ```bash
   cd database-migration
   pip install -r requirements.txt
   ```

2. **Set up Supabase (Source Database)**
   - Follow instructions in `source/README.md`
   - Create a Supabase project
   - Run the schema and seed data scripts

3. **Start MongoDB (Target Database)**
   ```bash
   cd sink
   docker-compose up -d
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase and MongoDB credentials
   ```

5. **Ready for demo!**
   - Source database is populated with sample data
   - Target database is running and ready
   - ETL directory is ready for live coding

## Demo Flow (20 minutes)

1. **Phase 1** (5 min): Explore the relational schema in Supabase
2. **Phase 2** (5 min): Design MongoDB document schema
3. **Phase 3** (8 min): Build ETL pipeline with Windsurf
4. **Phase 4** (2 min): Validate migration results

See `docs/demo_walkthrough.md` for detailed step-by-step instructions.

## Key Learning Points

- Relational vs Document data modeling
- Denormalization strategies
- ETL patterns for database migration
- Data validation techniques
- Using AI assistants for database work

## Documentation

- `docs/mongodb_best_practices.md` - MongoDB guidelines for AI agent
- `docs/demo_walkthrough.md` - Step-by-step demo script with prompts
- `source/README.md` - Supabase setup instructions
- `sink/README.md` - MongoDB setup instructions
- `etl/README.md` - ETL structure guidance

## License

MIT License - This is a demonstration project for educational purposes.
