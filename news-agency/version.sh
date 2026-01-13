#!/bin/bash

# Version Management Script for News Agency
# Usage:
#   ./version.sh bump patch    # 1.0.0 -> 1.0.1
#   ./version.sh bump minor    # 1.0.0 -> 1.1.0
#   ./version.sh bump major    # 1.0.0 -> 2.0.0
#   ./version.sh get           # Show current version

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/version.json"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is required but not installed."
    exit 1
fi

# Function to get current version
get_version() {
    jq -r '.version' "$VERSION_FILE"
}

# Function to bump version
bump_version() {
    local bump_type="$1"
    local current_version=$(get_version)

    # Parse current version
    IFS='.' read -r major minor patch <<< "$current_version"

    case "$bump_type" in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
        *)
            echo "❌ Invalid bump type. Use: major, minor, or patch"
            exit 1
            ;;
    esac

    new_version="${major}.${minor}.${patch}"

    # Update version.json
    jq ".version = \"$new_version\" | .build.date = \"$(date +%Y-%m-%d)\"" "$VERSION_FILE" > tmp.$$ && mv tmp.$$ "$VERSION_FILE"

    echo "✅ Version bumped: $current_version → $new_version"
    echo "📄 Updated: $VERSION_FILE"
}

# Function to show current status
show_status() {
    local current_version=$(get_version)
    local build_date=$(jq -r '.build.date' "$VERSION_FILE")

    echo "📦 Current Version: $current_version"
    echo "📅 Build Date: $build_date"

    # Show git info
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local git_sha=$(git rev-parse --short HEAD)
        local git_commits=$(git rev-list --count HEAD -- .)
        echo "🔗 Git SHA: $git_sha"
        echo "🔢 Git Commits: $git_commits"

        # Generate what the CI version would be
        local date_part=$(date +"%Y.%m.%d")
        local full_version="${current_version}-${date_part}.${git_commits}"
        echo "🏷️ CI Version: $full_version"
    fi
}

# Main script logic
case "${1:-}" in
    "bump")
        if [ -z "$2" ]; then
            echo "❌ Bump type required. Use: major, minor, or patch"
            exit 1
        fi
        bump_version "$2"
        ;;
    "get")
        get_version
        ;;
    "status"|"")
        show_status
        ;;
    *)
        echo "Usage: $0 [bump major|minor|patch] | [get] | [status]"
        echo ""
        echo "Examples:"
        echo "  $0 status          # Show current version info"
        echo "  $0 get             # Get current version only"
        echo "  $0 bump patch      # Increment patch version"
        echo "  $0 bump minor      # Increment minor version"
        echo "  $0 bump major      # Increment major version"
        exit 1
        ;;
esac