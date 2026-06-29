# Docker Database Password Reset

Quick reference for resetting user passwords in a Dockerized database when you can't log in to the web app.

## Problem

User locked out of web application (forgotten password, corrupted hash, etc.) and needs password reset via direct database access.

## Pattern: Docker → DB Container → Password Hash → Update

### Step 1: Find the database container and credentials

```bash
# List running containers
docker ps

# Check environment variables in the web container (DB credentials often passed here)
docker exec <web-container> printenv | grep -E "DB_|MYSQL_"

# Example output:
# DB_HOST=db
# DB_NAME=pos_system
# DB_USER=posuser
# DB_PASS=pospass
```

### Step 2: Generate a bcrypt hash

Most PHP/Node/Python apps use bcrypt for password hashing:

```bash
# From the web container (if PHP available)
docker exec <web-container> php -r "echo password_hash('admin123', PASSWORD_BCRYPT);"

# From the web container (if Node available)
docker exec <web-container> node -e "console.log(require('bcrypt').hashSync('admin123', 10))"

# From the web container (if Python available)
docker exec <web-container> python3 -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())"
```

**Output example:**
```
$2y$10$bK6ZJsPXoWLWuyk36JnMqelFtcm2LHI7ERIYyk4eZAXhJqJSmJCkG
```

### Step 3: Connect to the database and update

**MySQL:**

```bash
# Connect (suppress password warning by piping to grep)
docker exec <db-container> mysql -u <user> -p'<password>' <database> -e "SELECT id, username, email FROM users WHERE username = 'admin';" 2>&1 | grep -v "Warning"

# Update password
docker exec <db-container> mysql -u <user> -p'<password>' <database> -e "UPDATE users SET password = '\$2y\$10\$bK6ZJsPXoWLWuyk36JnMqelFtcm2LHI7ERIYyk4eZAXhJqJSmJCkG' WHERE username = 'admin';" 2>&1 | grep -v "Warning"

# Verify
docker exec <db-container> mysql -u <user> -p'<password>' <database> -e "SELECT id, username, LEFT(password, 20) as password_hash FROM users WHERE username = 'admin';" 2>&1 | grep -v "Warning"
```

**PostgreSQL:**

```bash
docker exec <db-container> psql -U <user> -d <database> -c "UPDATE users SET password = '\$2y\$10\$...' WHERE username = 'admin';"
```

### Step 4: Test login

Navigate to the app and log in with the new password (e.g., `admin123`).

## Common Pitfalls

**1. Wrong database user/password**
- Try credentials from `.env`, `docker-compose.yml`, or environment variables
- Common patterns: `root` user, `<appname>user`, `posuser`, etc.
- Passwords often match pattern: `<appname>_password`, `<appname>pass`

**2. MySQL "Access denied" errors**
- Error `Access denied for user 'root'@'localhost'` → trying wrong password
- Solution: extract actual password from `docker exec <web-container> printenv`
- Fallback: check `docker-compose.yml` for `MYSQL_ROOT_PASSWORD` or `MYSQL_PASSWORD`

**3. Escaping the bcrypt hash**
- Bcrypt hashes contain `$` which bash interprets as variable expansion
- **ALWAYS** wrap in single quotes: `'$2y$10$...'`
- In MySQL `-e` flag, escape further: `"\$2y\$10\$..."`

**4. Container TTY errors**
- Error: `cannot attach stdin to a TTY-enabled container`
- Cause: using `docker exec -it` when stdin is not a terminal
- Solution: remove `-it` flags → `docker exec <container> mysql ...`

## Example Session (from 2026-06-09)

```bash
# 1. Found credentials
docker exec secondhand-pos-web printenv | grep -E "DB_|MYSQL_"
# Output: DB_USER=posuser, DB_PASS=pospass

# 2. Generated hash
docker exec secondhand-pos-web php -r "echo password_hash('admin123', PASSWORD_BCRYPT);"
# Output: $2y$10$bK6ZJsPXoWLWuyk36JnMqelFtcm2LHI7ERIYyk4eZAXhJqJSmJCkG

# 3. List users
docker exec secondhand-pos-db mysql -u posuser -ppospass pos_system -e "SELECT id, username, email, role FROM users;" 2>&1 | grep -v "Warning"
# Output: 1	admin	admin@example.com	admin

# 4. Update password
docker exec secondhand-pos-db mysql -u posuser -ppospass pos_system -e "UPDATE users SET password = '\$2y\$10\$bK6ZJsPXoWLWuyk36JnMqelFtcm2LHI7ERIYyk4eZAXhJqJSmJCkG' WHERE username = 'admin';" 2>&1 | grep -v "Warning"

# 5. Verify
docker exec secondhand-pos-db mysql -u posuser -ppospass pos_system -e "SELECT id, username, LEFT(password, 20) as password_hash FROM users WHERE username = 'admin';" 2>&1 | grep -v "Warning"
# Output: 1	admin	$2y$10$bK6ZJsPXoWLWu

# 6. Test login → Success with admin:admin123
```

## When to Use This Pattern

- User forgot password and no "forgot password" flow exists
- Password reset email broken/not configured
- Initial admin account setup in fresh deployment
- Emergency access needed for production troubleshooting

## Security Note

This bypasses the application's authentication flow. Only use when:
- You have legitimate access to the server/containers
- The application doesn't have a working password reset mechanism
- It's for emergency admin access, not regular user management
