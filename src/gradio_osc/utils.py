def print_gradio_api(api_dict: dict):
    '''
    Print params and returns info for all endpoints in dict.
    Get a dict with gradio_client.view_api(return_type="dict")
    '''
    gradio_endpoints = api_dict["named_endpoints"]
    for endpoint_name, endpoint in gradio_endpoints.items():
        print(endpoint_name)
        params = endpoint['parameters']
        returns = endpoint['returns']
        for p in params:
            label = p['label']
            param_name = p['parameter_name']
            python_type = p['python_type']['type']
            has_default = p['parameter_has_default']
            param_default = p['parameter_default']
            # print(f"  - {param_name}: {python_type} ({label}, default: {param_default})")
            print(f"  - {param_name}: {python_type} {f"(default:{param_default})" if has_default else "[required]"}")
        print("  >> returns:")
        for p in returns:
            label = p['label']
            python_type = p['python_type']['type']
            # param_default = p['default']
            print(f"  -> {label}: {python_type}")
