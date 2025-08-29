"""
Tests for ts_config_loader module.

This test validates that the ts_config_loader can successfully parse
all TypeScript configuration files from the Balancer backend repository.
"""

import requests
from bal_tools.ts_config_loader import ts_config_loader


def test_all_backend_configs_load():
    """Test that all config files from Balancer backend can be loaded without errors."""
    
    # Get list of config files from GitHub API
    api_url = "https://api.github.com/repos/balancer/backend/contents/config?ref=v3-main"
    response = requests.get(api_url)
    response.raise_for_status()
    
    files = response.json()
    
    # Filter for .ts files (excluding index.ts)
    config_files = [f['name'] for f in files if f['name'].endswith('.ts') and f['name'] != 'index.ts']
    
    assert len(config_files) > 0, "No config files found"
    
    failed_configs = []
    
    for config_file in config_files:
        chain = config_file.replace('.ts', '')
        url = f"https://raw.githubusercontent.com/balancer/backend/refs/heads/v3-main/config/{config_file}"
        
        try:
            # Should not raise any exceptions
            config = ts_config_loader(url)
            assert isinstance(config, dict), f"Config for {chain} should be a dictionary"
        except Exception as e:
            failed_configs.append((chain, str(e)))
    
    assert len(failed_configs) == 0, f"Failed to load {len(failed_configs)} configs: {failed_configs}"