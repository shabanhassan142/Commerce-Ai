"""Live end-to-end verification for Module 5."""
import asyncio
import httpx


async def test_live_module5():
    print("=" * 60)
    print("MODULE 5 LIVE END-TO-END VERIFICATION")
    print("=" * 60)

    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1", timeout=60.0) as client:
        # 1. Login as customer
        cust_login = await client.post(
            "/auth/login",
            json={"email": "customer1@example.com", "password": "Customer123!"},
        )
        assert cust_login.status_code == 200, cust_login.text
        cust_token = cust_login.json()["data"]["tokens"]["access_token"]
        cust_h = {"Authorization": f"Bearer {cust_token}"}

        # 2. Login as support staff
        sup_login = await client.post(
            "/auth/login",
            json={"email": "support@commerceflow.ai", "password": "Support123!"},
        )
        assert sup_login.status_code == 200, sup_login.text
        sup_token = sup_login.json()["data"]["tokens"]["access_token"]
        sup_user_id = sup_login.json()["data"]["user"]["id"]
        sup_h = {"Authorization": f"Bearer {sup_token}"}

        # 3. Login as admin
        adm_login = await client.post(
            "/auth/login",
            json={"email": "admin@commerceflow.ai", "password": "Admin123!"},
        )
        assert adm_login.status_code == 200, adm_login.text
        adm_token = adm_login.json()["data"]["tokens"]["access_token"]
        adm_h = {"Authorization": f"Bearer {adm_token}"}

        print("\n[+] Authentication succeeded for Customer, Support, and Admin")

        # 4. Customer creates a ticket
        create_res = await client.post(
            "/tickets",
            headers=cust_h,
            json={
                "subject": "Damaged package delivered",
                "description": "The item inside was cracked upon arrival.",
                "priority": "high",
            },
        )
        assert create_res.status_code == 201, create_res.text
        ticket = create_res.json()["data"]
        ticket_id = ticket["id"]
        print(f"  [+] Customer created ticket {ticket['ticket_number']} (Status: {ticket['status']}, SLA: {ticket['sla_deadline'][:19]})")

        # 5. Customer lists own tickets
        my_tickets = await client.get("/my/tickets", headers=cust_h)
        assert my_tickets.status_code == 200, my_tickets.text
        print(f"  [+] /my/tickets returned {my_tickets.json()['data']['total']} tickets for customer")

        # 6. Support assigns ticket to self
        assign_res = await client.patch(
            f"/tickets/{ticket_id}/assign",
            headers=sup_h,
            json={"agent_id": sup_user_id},
        )
        assert assign_res.status_code == 200, assign_res.text
        print(f"  [+] Support assigned ticket to self (Status: {assign_res.json()['data']['status']})")

        # 7. Support updates priority to URGENT
        pri_res = await client.patch(
            f"/tickets/{ticket_id}/priority",
            headers=sup_h,
            json={"priority": "urgent"},
        )
        assert pri_res.status_code == 200, pri_res.text
        print(f"  [+] Priority updated to URGENT (New SLA Deadline: {pri_res.json()['data']['sla_deadline'][:19]})")

        # 8. Support adds internal note
        note_res = await client.post(
            f"/tickets/{ticket_id}/notes",
            headers=sup_h,
            json={"content": "Customer requested immediate replacement item."},
        )
        assert note_res.status_code == 201, note_res.text
        print("  [+] Support added internal note")

        # 9. Verify Customer cannot see internal notes
        cust_view = await client.get(f"/my/tickets/{ticket_id}", headers=cust_h)
        assert cust_view.status_code == 200
        assert cust_view.json()["data"]["notes"] == []
        print("  [+] Verified: Internal notes remain hidden from customer")

        # 10. Customer posts a reply
        reply_res = await client.post(
            f"/my/tickets/{ticket_id}/reply",
            headers=cust_h,
            json={"content": "I attached photos of the damage.", "attachment_placeholder": "damage.png"},
        )
        assert reply_res.status_code == 201, reply_res.text
        print("  [+] Customer posted reply")

        # 11. Support updates status to IN_PROGRESS, then RESOLVED, then CLOSED
        inp_status = await client.patch(
            f"/tickets/{ticket_id}/status",
            headers=sup_h,
            json={"status": "in_progress"},
        )
        assert inp_status.status_code == 200, inp_status.text
        print("  [+] Status updated to IN_PROGRESS")

        res_status = await client.patch(
            f"/tickets/{ticket_id}/status",
            headers=sup_h,
            json={"status": "resolved"},
        )
        assert res_status.status_code == 200, res_status.text
        print("  [+] Status updated to RESOLVED")

        closed_status = await client.patch(
            f"/tickets/{ticket_id}/status",
            headers=sup_h,
            json={"status": "closed"},
        )
        assert closed_status.status_code == 200, closed_status.text
        print("  [+] Status updated to CLOSED")

        # 12. Admin views Support Dashboard Stats
        dash_res = await client.get("/dashboard/stats", headers=adm_h)
        assert dash_res.status_code == 200, dash_res.text
        dash = dash_res.json()["data"]
        print(f"\n[+] Support Dashboard Stats:")
        print(f"    - Open Tickets: {dash['open_tickets']}")
        print(f"    - Assigned Tickets: {dash['assigned_tickets']}")
        print(f"    - Resolved Today: {dash['resolved_today']}")
        print(f"    - Urgent Tickets: {dash['urgent_tickets']}")
        print(f"    - AI Resolution %: {dash['ai_resolution_percent']}%")

    print("\n" + "=" * 60)
    print("MODULE 5 LIVE END-TO-END VERIFICATION SUCCESSFUL!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_live_module5())
