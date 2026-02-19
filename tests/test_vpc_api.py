from fastapi import status


def test_list_vpcs_empty(client):
    response = client.get("/vpc")
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["count"] == 0
    assert payload["vpcs"] == []


def test_get_vpc_not_found(client):
    response = client.get("/vpc/vpc-unknown")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_vpc_and_list(client, monkeypatch):
    def _fake_provision(request, created_by, repo):
        record = {
            "vpc_id": "vpc-123",
            "vpc_name": request.vpc_name,
            "vpc_cidr": request.vpc_cidr,
            "igw_id": "igw-1",
            "region": "us-east-1",
            "subnets": [
                {
                    "subnet_id": "subnet-1",
                    "cidr": "10.0.1.0/24",
                    "availability_zone": "us-east-1a",
                    "name": "public-1",
                }
            ],
            "tags": request.tags,
            "created_by": created_by,
            "created_at": "2026-02-19T00:00:00+00:00",
            "status": "active",
        }
        repo.save(record)
        return record

    monkeypatch.setattr("app.apis.vpc.provision_vpc", _fake_provision)

    payload = {
        "vpc_cidr": "10.0.0.0/16",
        "vpc_name": "demo-vpc",
        "subnets": [{"cidr": "10.0.1.0/24", "az": "us-east-1a", "name": "public-1"}],
        "tags": {"Environment": "test"},
    }
    create_resp = client.post("/vpc", json=payload)
    assert create_resp.status_code == status.HTTP_201_CREATED

    list_resp = client.get("/vpc")
    assert list_resp.status_code == status.HTTP_200_OK
    data = list_resp.json()
    assert data["count"] == 1
    assert data["vpcs"][0]["vpc_id"] == "vpc-123"


def test_delete_vpc_not_found(client):
    resp = client.delete("/vpc/vpc-missing")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_delete_vpc_success(client, monkeypatch):
    def _fake_remove(vpc_id, repo):
        return True

    monkeypatch.setattr("app.apis.vpc.remove_vpc_record", _fake_remove)
    resp = client.delete("/vpc/vpc-123")
    assert resp.status_code == status.HTTP_204_NO_CONTENT
