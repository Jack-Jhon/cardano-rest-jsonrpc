#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import requests
import json


def main():
    url = "http://localhost:4000/jsonrpc"

    # Example echo method
    payload = {
        "method": "foobar",
        # "params": [1,2],
        "params": {"foo": 2, "bar": 9999},
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(url, json=payload).json()
    print(response)
    # assert response["result"] == "echome!"
    # assert response["jsonrpc"]
    # assert response["id"] == 0

if __name__ == "__main__":
    main()