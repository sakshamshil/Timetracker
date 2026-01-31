#!/bin/bash
#
# One-line installer for timetrack CLI
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/timetrack/main/install-remote.sh | bash
#

set -e

REPO_URL="https://github.com/sakshamshil/Timetracker.git"
INSTALL_DIR="$HOME/.timetrack-repo"
APP_NAME="track"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}⚪ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version (need 3.8+)
check_python() {
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi

    local python_version
    python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    local major_version
    local minor_version
    major_version=$(echo "$python_version" | cut -d. -f1)
    minor_version=$(echo "$python_version" | cut -d. -f2)

    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 8 ]); then
        print_error "Python 3.8 or higher is required. Found: $python_version"
        exit 1
    fi

    print_success "Python $python_version found"
}

# Install pipx if not present
install_pipx() {
    if command_exists pipx; then
        print_success "pipx is already installed"
        return
    fi

    print_info "Installing pipx..."

    if ! command_exists pip3; then
        print_error "pip3 is not installed. Please install pip first."
        exit 1
    fi

    python3 -m pip install --user pipx
    python3 -m pipx ensurepath

    # Source the updated PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    if ! command_exists pipx; then
        print_error "pipx installation failed. Please try installing manually:"
        echo "  python3 -m pip install --user pipx"
        echo "  python3 -m pipx ensurepath"
        exit 1
    fi

    print_success "pipx installed successfully"
}

# Clone or update the repository
clone_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        print_info "Existing installation found at $INSTALL_DIR"
        print_info "Updating to latest version..."
        cd "$INSTALL_DIR"
        git pull origin main || {
            print_error "Failed to update repository. You may have local changes."
            print_info "To force a clean install, remove the directory: rm -rf $INSTALL_DIR"
            exit 1
        }
    else
        print_info "Cloning repository to $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    print_success "Repository ready at $INSTALL_DIR"
}

# Install the application
install_app() {
    print_info "Installing timetrack CLI..."

    # Check if already installed
    if pipx list | grep -q "track"; then
        print_info "Existing installation found. Reinstalling..."
        pipx reinstall track || pipx uninstall track
    fi

    # Install in editable mode so updates work with git pull
    pipx install -e "$INSTALL_DIR"

    if ! command_exists track; then
        print_error "Installation failed. The 'track' command is not available."
        print_info "You may need to restart your terminal or run: source ~/.bashrc"
        exit 1
    fi

    print_success "timetrack CLI installed successfully!"
}

# Verify installation
verify_install() {
    print_info "Verifying installation..."

    if command_exists track; then
        local version
        version=$(track --version 2>/dev/null || echo "unknown")
        print_success "track command is available"
        track --help | head -20
        echo ""
        print_success "Installation complete! Run 'track --help' to get started."
    else
        print_error "Verification failed. Please try restarting your terminal."
        exit 1
    fi
}

# Main installation flow
main() {
    echo "================================"
    echo "  Timetrack CLI Installer"
    echo "================================"
    echo ""

    check_python
    install_pipx
    clone_repo
    install_app
    verify_install

    echo ""
    echo "================================"
    print_success "Installation successful!"
    echo "================================"
    echo ""
    echo "Quick start:"
    echo "  track start 'My first task'"
    echo "  track status"
    echo "  track stop"
    echo ""
    echo "To update in the future, run:"
    echo "  track update"
    echo ""
}

# Run main function
main
