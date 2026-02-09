"""Tests for the Mergington High School API."""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test."""
    original_state = {}
    for name, details in activities.items():
        original_state[name] = details["participants"].copy()
    
    yield
    
    # Restore original state
    for name in activities:
        activities[name]["participants"] = original_state[name].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_activities_have_initial_participants(self, client):
        """Test that activities have their initial participants."""
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_new_participant(self, client):
        """Test signing up a new participant."""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up newstudent@mergington.edu for Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist."""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_already_registered(self, client):
        """Test signing up when already registered."""
        response = client.post(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_activities(self, client):
        """Test same student can sign up for multiple activities."""
        email = "versatile@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            f"/activities/Programming%20Class/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify student is in both
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant."""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered michael@mergington.edu from Chess Club" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist."""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering when not registered."""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_signup_then_unregister(self, client):
        """Test signing up and then unregistering."""
        email = "tempstudent@mergington.edu"
        
        # Sign up
        signup_response = client.post(
            f"/activities/Tennis%20Club/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Tennis Club"]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/Tennis%20Club/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        assert email not in activities_response.json()["Tennis Club"]["participants"]


class TestParticipantCounts:
    """Tests for verifying participant counts are correct."""
    
    def test_initial_participant_counts(self, client):
        """Test that initial participant counts are correct."""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 2
        assert len(data["Programming Class"]["participants"]) == 2
        assert len(data["Basketball Team"]["participants"]) == 1
    
    def test_count_increases_after_signup(self, client):
        """Test that participant count increases after signup."""
        response_before = client.get("/activities")
        count_before = len(response_before.json()["Art Studio"]["participants"])
        
        client.post("/activities/Art%20Studio/signup?email=newart@mergington.edu")
        
        response_after = client.get("/activities")
        count_after = len(response_after.json()["Art Studio"]["participants"])
        
        assert count_after == count_before + 1
    
    def test_count_decreases_after_unregister(self, client):
        """Test that participant count decreases after unregister."""
        original_participant = "michael@mergington.edu"
        
        response_before = client.get("/activities")
        count_before = len(response_before.json()["Chess Club"]["participants"])
        
        client.delete(
            f"/activities/Chess%20Club/unregister?email={original_participant}"
        )
        
        response_after = client.get("/activities")
        count_after = len(response_after.json()["Chess Club"]["participants"])
        
        assert count_after == count_before - 1
