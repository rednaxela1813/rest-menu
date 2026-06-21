"""Role-based access control for staff screens."""
import pytest
from django.urls import reverse

from tests import factories

pytestmark = pytest.mark.django_db


def test_guest_cannot_access_kitchen(client):
    resp = client.get(reverse("kitchen:board"))
    assert resp.status_code in (302, 403)  # redirect to login


def test_guest_cannot_access_cashier(client):
    resp = client.get(reverse("cashier:board"))
    assert resp.status_code in (302, 403)


def test_kitchen_user_forbidden_on_cashier_board(client, kitchen_user, restaurant):
    client.force_login(kitchen_user)
    resp = client.get(reverse("cashier:board"))
    assert resp.status_code == 403


def test_cashier_can_open_board(client, cashier, restaurant):
    client.force_login(cashier)
    resp = client.get(reverse("cashier:board"))
    assert resp.status_code == 200


def test_cashier_cannot_download_qr_pdf(client, cashier):
    client.force_login(cashier)
    resp = client.get(reverse("tables:qr_pdf"))
    assert resp.status_code == 403


def test_admin_can_download_qr_pdf(client, admin_user, restaurant):
    factories.DiningTableFactory(restaurant=restaurant)
    client.force_login(admin_user)
    resp = client.get(reverse("tables:qr_pdf"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"


def test_kitchen_can_open_board(client, kitchen_user, restaurant):
    client.force_login(kitchen_user)
    resp = client.get(reverse("kitchen:board"))
    assert resp.status_code == 200
