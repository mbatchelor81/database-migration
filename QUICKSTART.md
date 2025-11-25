# Quick Start Guide

Get your demo environment ready in 5 minutes.

## 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## 2. Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a project
2. In SQL Editor, run `source/schema.sql`
3. In SQL Editor, run `source/seed_data.sql`
4. Copy your credentials to `.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

## 3. Start MongoDB

```bash
cd sink
docker-compose up -d
cd ..
```

## 4. Verify Setup

```bash
# Test Supabase
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print('✓ Supabase connected')"

# Test MongoDB
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI')); print('✓ MongoDB connected')"
```

## 5. Ready for Demo!

Open these files in your IDE:
- `docs/demo_walkthrough.md` - Your step-by-step guide with prompts
- `docs/mongodb_best_practices.md` - For agent reference
- `source/schema.sql` - To show the relational schema

## Demo Flow

Follow the prompts in `docs/demo_walkthrough.md`:

1. **Phase 1** (5 min): Explore relational schema
2. **Phase 2** (5 min): Design MongoDB schema  
3. **Phase 3** (8 min): Build ETL pipeline
4. **Phase 4** (2 min): Validate migration

## Troubleshooting

**Supabase connection fails:**
- Check your `.env` has correct `SUPABASE_URL` and `SUPABASE_KEY`
- Verify project is not paused in Supabase dashboard

**MongoDB connection fails:**
- Check Docker is running: `docker ps`
- Restart container: `cd sink && docker-compose restart`

**Import errors:**
- Ensure virtual environment is activated
- Reinstall: `pip install -r requirements.txt --force-reinstall`

## After Demo

```bash
# Stop MongoDB
cd sink
docker-compose down

# Deactivate virtual environment
deactivate
```

## Need Help?

- Full walkthrough: `docs/demo_walkthrough.md`
- MongoDB guidelines: `docs/mongodb_best_practices.md`
- Source setup: `source/README.md`
- Sink setup: `sink/README.md`
- ETL guidance: `etl/README.md`
