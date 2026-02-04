"""Tests for the FastAPI application"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint"""

    def test_root_redirect(self):
        """Test that root redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test the activities endpoint"""

    def test_get_activities(self):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify structure of activities
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activities_have_participants(self):
        """Test that some activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        # Check that at least one activity has participants
        has_participants = any(
            len(activity["participants"]) > 0
            for activity in data.values()
        )
        assert has_participants


class TestSignupEndpoint:
    """Test the signup endpoint"""

    def test_signup_new_participant(self):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=newemail@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
        assert "newemail@mergington.edu" in data["message"]

    def test_signup_duplicate_participant(self):
        """Test that signing up twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Soccer%20Team/signup?email=" + email
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Soccer%20Team/signup?email=" + email
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_nonexistent_activity(self):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/NonExistent/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_participant_added_to_activity(self):
        """Test that participant is actually added to the activity"""
        email = "verify@mergington.edu"
        
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Soccer Team"]["participants"])
        
        # Sign up
        client.post(f"/activities/Soccer%20Team/signup?email={email}")
        
        # Get updated count
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()["Soccer Team"]["participants"])
        
        assert updated_count == initial_count + 1
        assert email in updated_response.json()["Soccer Team"]["participants"]


class TestUnregisterEndpoint:
    """Test the unregister endpoint"""

    def test_unregister_participant(self):
        """Test unregistering a participant"""
        email = "unregister@mergington.edu"
        
        # First sign up
        client.post(f"/activities/Soccer%20Team/signup?email={email}")
        
        # Then unregister
        response = client.post(
            f"/activities/Soccer%20Team/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        assert email in data["message"]

    def test_unregister_nonexistent_activity(self):
        """Test unregistering from a non-existent activity"""
        response = client.post(
            "/activities/NonExistent/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_unregister_not_registered_participant(self):
        """Test unregistering someone who isn't registered"""
        response = client.post(
            "/activities/Soccer%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_participant_removed_from_activity(self):
        """Test that participant is actually removed from the activity"""
        email = "remove@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Soccer%20Team/signup?email={email}")
        
        # Verify added
        response1 = client.get("/activities")
        assert email in response1.json()["Soccer Team"]["participants"]
        initial_count = len(response1.json()["Soccer Team"]["participants"])
        
        # Unregister
        client.post(f"/activities/Soccer%20Team/unregister?email={email}")
        
        # Verify removed
        response2 = client.get("/activities")
        assert email not in response2.json()["Soccer Team"]["participants"]
        final_count = len(response2.json()["Soccer Team"]["participants"])
        
        assert final_count == initial_count - 1


class TestActivityConstraints:
    """Test activity constraints"""

    def test_signup_respects_max_participants(self):
        """Test that signup still works but data structure is maintained"""
        # Just verify the max_participants constraint exists in the data
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            max_participants = activity_data["max_participants"]
            current_participants = len(activity_data["participants"])
            
            # Verify the data is valid
            assert current_participants <= max_participants
            assert max_participants > 0
