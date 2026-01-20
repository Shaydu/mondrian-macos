#!/usr/bin/env python3
"""
RunPod Deployment Script for Mondrian Photography Advisor

This script deploys the Mondrian Docker image to RunPod using their API.
Requires: RunPod API key (get from https://www.runpod.io/console/api-keys)

Usage:
    python3 deploy_to_runpod.py --api-key YOUR_API_KEY [--name pod-name] [--gpu-id A40]
"""

import argparse
import json
import sys
import time
from typing import Optional
import requests

# RunPod API endpoints
RUNPOD_API_URL = "https://api.runpod.io/graphql"
RUNPOD_ENDPOINT_URL = "https://api.runpod.io/graphql"

# GraphQL mutation to create a pod
CREATE_POD_MUTATION = """
mutation {
  podFindAndDeployOnDemand(
    input: {
      cloudType: ALL
      gpuCount: 1
      volumeInGb: 50
      containerDiskInGb: 0
      minVolumeInGb: 50
      gpuTypeId: "%s"
      name: "%s"
      imageName: "%s"
      ports: "%s"
      containerRegistry: "%s"
      volumeMountPath: "/workspace"
      env: [
        {key: "PYTHONUNBUFFERED", value: "1"}
        {key: "PYTORCH_CUDA_ALLOC_CONF", value: "expandable_segments:True"}
        {key: "MODE", value: "lora+rag"}
        {key: "BACKEND", value: "bnb"}
      ]
      startSsh: true
    }
  ) {
    id
    machineId
    machine {
      gpuCount
    }
    desiredStatus
  }
}
"""

# GraphQL query to get pod status
GET_POD_STATUS_QUERY = """
query {
  pod(input: {podId: "%s"}) {
    id
    name
    status
    runtime {
      gpus {
        gpuUtilization
        memoryUtilization
      }
      ports {
        isIpPublic
        publicIp
        publicPort
        privatePort
        type
      }
    }
  }
}
"""


def deploy_to_runpod(
    api_key: str,
    image: str = "shaydu/mondrian:latest",
    pod_name: str = "mondrian-advisor",
    gpu_type: str = "A40",
    volume_size: int = 50,
) -> Optional[dict]:
    """
    Deploy Mondrian to RunPod.
    
    Args:
        api_key: RunPod API key
        image: Docker image to deploy
        pod_name: Name for the pod
        gpu_type: GPU type (A40, A6000, RTX3090, etc.)
        volume_size: Volume size in GB
    
    Returns:
        Pod details dict or None if failed
    """
    
    print(f"🚀 Deploying Mondrian to RunPod...")
    print(f"   Image: {image}")
    print(f"   GPU: {gpu_type}")
    print(f"   Volume: {volume_size}GB")
    print()
    
    # Port configuration
    ports = "5005/http,5006/http,5100/http"
    
    # Build mutation
    mutation = CREATE_POD_MUTATION % (
        gpu_type,
        pod_name,
        image,
        ports,
        "docker",
    )
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    payload = {
        "query": mutation,
    }
    
    try:
        print("📤 Sending deployment request to RunPod...")
        response = requests.post(
            RUNPOD_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        
        result = response.json()
        
        if "errors" in result:
            print("❌ API Error:")
            for error in result["errors"]:
                print(f"   {error.get('message', 'Unknown error')}")
            return None
        
        pod_data = result.get("data", {}).get("podFindAndDeployOnDemand", {})
        
        if not pod_data or not pod_data.get("id"):
            print("❌ Failed to create pod")
            print(f"Response: {json.dumps(result, indent=2)}")
            return None
        
        pod_id = pod_data["id"]
        print(f"✅ Pod created successfully!")
        print(f"   Pod ID: {pod_id}")
        print(f"   Status: {pod_data.get('desiredStatus', 'pending')}")
        
        return pod_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return None


def get_pod_status(api_key: str, pod_id: str) -> Optional[dict]:
    """Get detailed pod status and endpoint info."""
    
    query = GET_POD_STATUS_QUERY % pod_id
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    payload = {"query": query}
    
    try:
        response = requests.post(
            RUNPOD_API_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        
        result = response.json()
        
        if "errors" in result:
            return None
        
        return result.get("data", {}).get("pod", {})
        
    except Exception as e:
        print(f"❌ Error getting pod status: {e}")
        return None


def monitor_pod_startup(api_key: str, pod_id: str, max_wait: int = 300) -> bool:
    """Monitor pod startup and get public endpoint."""
    
    print(f"\n⏳ Monitoring pod startup (this may take 2-5 minutes)...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        pod_status = get_pod_status(api_key, pod_id)
        
        if not pod_status:
            time.sleep(5)
            continue
        
        status = pod_status.get("status", "provisioning")
        
        print(f"   Status: {status}")
        
        # Check if pod is running and has public IP
        if status == "RUNNING":
            runtime = pod_status.get("runtime", {})
            ports = runtime.get("ports", [])
            
            if ports:
                print(f"\n✅ Pod is RUNNING!")
                print(f"   Pod ID: {pod_id}")
                print(f"\n📍 Exposed Endpoints:")
                
                endpoints = {}
                for port_info in ports:
                    if port_info.get("isIpPublic"):
                        public_ip = port_info.get("publicIp")
                        public_port = port_info.get("publicPort")
                        private_port = port_info.get("privatePort")
                        
                        if private_port == 5005:
                            service = "Job Service"
                        elif private_port == 5006:
                            service = "Summary Service"
                        elif private_port == 5100:
                            service = "AI Advisor"
                        else:
                            service = "Unknown"
                        
                        url = f"http://{public_ip}:{public_port}"
                        endpoints[service] = url
                        print(f"   {service} (:{private_port})")
                        print(f"     → {url}")
                
                # For iOS app
                print(f"\n📱 iOS App Configuration:")
                if "Job Service" in endpoints:
                    advisors_url = endpoints["Job Service"] + "/advisors"
                    print(f"   GET /advisors endpoint:")
                    print(f"     → {advisors_url}")
                
                return True
        
        time.sleep(5)
    
    print(f"\n⚠️  Pod did not reach RUNNING status within {max_wait} seconds")
    print(f"   Check RunPod console for details: https://www.runpod.io/console/pods")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Mondrian to RunPod"
    )
    parser.add_argument(
        "--api-key",
        required=False,
        help="RunPod API key (or set RUNPOD_API_KEY env var)",
    )
    parser.add_argument(
        "--name",
        default="mondrian-advisor",
        help="Pod name (default: mondrian-advisor)",
    )
    parser.add_argument(
        "--image",
        default="shaydu/mondrian:latest",
        help="Docker image (default: shaydu/mondrian:latest)",
    )
    parser.add_argument(
        "--gpu",
        default="A40",
        help="GPU type (default: A40). Options: A100, A6000, RTX3090, etc.",
    )
    parser.add_argument(
        "--volume-size",
        type=int,
        default=50,
        help="Volume size in GB (default: 50)",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor pod startup until ready",
    )
    
    args = parser.parse_args()
    
    # Get API key from argument or environment
    import os
    api_key = args.api_key or os.getenv("RUNPOD_API_KEY")
    
    if not api_key:
        print("❌ Error: RunPod API key required")
        print("\nProvide via:")
        print("  1. --api-key argument")
        print("  2. RUNPOD_API_KEY environment variable")
        print("\nGet your API key: https://www.runpod.io/console/api-keys")
        sys.exit(1)
    
    # Deploy pod
    pod_data = deploy_to_runpod(
        api_key=api_key,
        image=args.image,
        pod_name=args.name,
        gpu_type=args.gpu,
        volume_size=args.volume_size,
    )
    
    if not pod_data:
        sys.exit(1)
    
    pod_id = pod_data["id"]
    
    # Monitor if requested
    if args.monitor or True:  # Always monitor for user convenience
        success = monitor_pod_startup(api_key, pod_id)
        if not success:
            print(f"\n💡 Tip: Check pod status at:")
            print(f"   https://www.runpod.io/console/pods/{pod_id}")
    else:
        print(f"\n💡 Pod created. Check status at:")
        print(f"   https://www.runpod.io/console/pods/{pod_id}")
    
    print("\n" + "="*60)
    print("📋 Deployment Summary")
    print("="*60)
    print(f"Pod ID: {pod_id}")
    print(f"Pod Name: {args.name}")
    print(f"Image: {args.image}")
    print(f"GPU: {args.gpu}")
    print(f"\nManage pod: https://www.runpod.io/console/pods/{pod_id}")
    print("="*60)


if __name__ == "__main__":
    main()
