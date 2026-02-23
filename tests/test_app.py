"""
Tests for the Mergington High School Activities API

Uses the AAA (Arrange-Act-Assert) pattern:
- Arrange: Set up test data and fixtures
- Act: Execute the code being tested
- Assert: Verify the results
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Fixture: Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def fresh_activities():
    """
    Fixture: Reset activities database to a clean state for each test.
    Uses the Arrange step of AAA pattern.
    """
    # Store original state
    original_activities = activities.copy()
    
    # Clear and populate with test data
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 2,
            "participants": ["alice@test.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 3,
            "participants": []
        },
        "Full Activity": {
            "description": "An activity at capacity",
            "schedule": "Mondays, 2:00 PM - 3:00 PM",
            "max_participants": 1,
            "participants": ["bob@test.edu"]
        }
    })
    
    yield activities
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities_success(self, client, fresh_activities):
        """
        Test: Retrieving all activities returns success with correct structure
        
        Arrange: Test data is in fresh_activities fixture
        Act: Make GET request to /activities
        Assert: Verify 200 status and response contains expected activities
        """
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Full Activity" in data
        assert len(data) == 3
    
    def test_get_activities_contains_required_fields(self, client, fresh_activities):
        """
        Test: Each activity has required fields
        
        Arrange: Test data is in fresh_activities fixture
        Act: Make GET request and extract first activity
        Assert: Verify all required fields are present
        """
        # Act
        response = client.get("/activities")
        activities_data = response.json()
        chess_club = activities_data["Chess Club"]
        
        # Assert
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
    
    def test_get_activities_shows_current_participants(self, client, fresh_activities):
        """
        Test: Participant list is returned correctly
        
        Arrange: Chess Club has alice@test.edu in participants
        Act: Get activities and check Chess Club
        Assert: Verify correct participants are shown
        """
        # Act
        response = client.get("/activities")
        activities_data = response.json()
        
        # Assert
        assert activities_data["Chess Club"]["participants"] == ["alice@test.edu"]
        assert activities_data["Programming Class"]["participants"] == []


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, fresh_activities):
        """
        Test: Student successfully signs up for an activity
        
        Arrange: Programming Class has 0 participants, 1 spot available
        Act: POST signup request with valid email and activity
        Assert: Verify 200 status and success message
        """
        # Act
        response = client.post(
            "/activities/Programming Class/signup?email=charlie@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
        assert "charlie@test.edu" in response.json()["message"]
        assert "Programming Class" in response.json()["message"]
    
    def test_signup_adds_participant_to_activity(self, client, fresh_activities):
        """
        Test: Participant is actually added to activity's participants list
        
        Arrange: Programming Class has 0 participants
        Act: Sign up a student and verify by fetching activities
        Assert: Verify participant count increases
        """
        # Act
        client.post("/activities/Programming Class/signup?email=david@test.edu")
        response = client.get("/activities")
        
        # Assert
        updated_programming = response.json()["Programming Class"]
        assert "david@test.edu" in updated_programming["participants"]
        assert len(updated_programming["participants"]) == 1
    
    def test_signup_activity_not_found(self, client, fresh_activities):
        """
        Test: Signing up for non-existent activity returns 404
        
        Arrange: No "Nonexistent Club" in activities
        Act: POST signup for non-existent activity
        Assert: Verify 404 status and error message
        """
        # Act
        response = client.post(
            "/activities/Nonexistent Club/signup?email=eve@test.edu"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_activity_full(self, client, fresh_activities):
        """
        Test: Signing up for full activity returns 400
        
        Arrange: Full Activity has max_participants=1 and 1 participant (bob)
        Act: POST signup for the full activity
        Assert: Verify 400 status and "Activity is full" message
        """
        # Act
        response = client.post(
            "/activities/Full Activity/signup?email=frank@test.edu"
        )
        
        # Assert
        assert response.status_code == 400
        assert "Activity is full" in response.json()["detail"]
    
    def test_signup_duplicate_student(self, client, fresh_activities):
        """
        Test: Student cannot sign up twice for same activity
        
        Arrange: alice@test.edu is already in Chess Club
        Act: POST signup for Chess Club with same email
        Assert: Verify 400 status and duplicate error message
        """
        # Act
        response = client.post(
            "/activities/Chess Club/signup?email=alice@test.edu"
        )
        
        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_same_student_different_activities(self, client, fresh_activities):
        """
        Test: Same student can sign up for different activities
        
        Arrange: alice@test.edu is in Chess Club, Programming Class is open
        Act: Sign up alice for Programming Class
        Assert: Verify 200 status - success
        """
        # Act
        response = client.post(
            "/activities/Programming Class/signup?email=alice@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
        activities_data = client.get("/activities").json()
        assert "alice@test.edu" in activities_data["Programming Class"]["participants"]
    
    def test_signup_respects_capacity_limit(self, client, fresh_activities):
        """
        Test: Can add multiple students up to capacity limit
        
        Arrange: Programming Class has max_participants=3
        Act: Sign up multiple students sequentially
        Assert: Verify all are added until capacity is reached
        """
        # Act - Sign up 2 more students (1 spot left)
        response1 = client.post(
            "/activities/Programming Class/signup?email=liam@test.edu"
        )
        response2 = client.post(
            "/activities/Programming Class/signup?email=mia@test.edu"
        )
        
        # Assert both succeeded
        assert response1.status_code == 200
        assert response2.status_code == 200
        activities_data = client.get("/activities").json()
        assert len(activities_data["Programming Class"]["participants"]) == 2


class TestUnregisterParticipant:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, fresh_activities):
        """
        Test: Student successfully unregisters from activity
        
        Arrange: alice@test.edu is in Chess Club
        Act: DELETE request to unregister from Chess Club
        Assert: Verify 200 status and success message
        """
        # Act
        response = client.delete(
            "/activities/Chess Club/unregister?email=alice@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
        assert "alice@test.edu" in response.json()["message"]
        assert "Unregistered" in response.json()["message"]
    
    def test_unregister_removes_participant(self, client, fresh_activities):
        """
        Test: Participant is actually removed from activity's list
        
        Arrange: alice@test.edu is in Chess Club
        Act: Unregister and fetch activities to verify
        Assert: Verify participant count decreases
        """
        # Act
        client.delete("/activities/Chess Club/unregister?email=alice@test.edu")
        response = client.get("/activities")
        
        # Assert
        updated_chess = response.json()["Chess Club"]
        assert "alice@test.edu" not in updated_chess["participants"]
        assert len(updated_chess["participants"]) == 0
    
    def test_unregister_activity_not_found(self, client, fresh_activities):
        """
        Test: Unregistering from non-existent activity returns 404
        
        Arrange: No "Phantom Club" in activities
        Act: DELETE unregister for non-existent activity
        Assert: Verify 404 status
        """
        # Act
        response = client.delete(
            "/activities/Phantom Club/unregister?email=alice@test.edu"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_student_not_registered(self, client, fresh_activities):
        """
        Test: Unregistering non-existent student returns 400
        
        Arrange: grace@test.edu is not in any activity
        Act: DELETE unregister for student not in activity
        Assert: Verify 400 status and error message
        """
        # Act
        response = client.delete(
            "/activities/Chess Club/unregister?email=grace@test.edu"
        )
        
        # Assert
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_frees_spot_for_signup(self, client, fresh_activities):
        """
        Test: After unregistering, someone else can sign up
        
        Arrange: Full Activity is at capacity (bob@test.edu)
        Act: Unregister bob, then try to sign up henry
        Assert: Verify henry can successfully sign up
        """
        # Act - First unregister
        client.delete("/activities/Full Activity/unregister?email=bob@test.edu")
        
        # Act - Now try to sign up new person
        response = client.post(
            "/activities/Full Activity/signup?email=henry@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
        activities_data = client.get("/activities").json()
        assert "henry@test.edu" in activities_data["Full Activity"]["participants"]
        assert "bob@test.edu" not in activities_data["Full Activity"]["participants"]


class TestRootEndpoint:
    """Tests for GET / endpoint"""
    
    def test_root_redirect(self, client):
        """
        Test: Root endpoint redirects to static index.html
        
        Arrange: Test client ready
        Act: GET request to /
        Assert: Verify redirect status (307 or 308)
        """
        # Act
        response = client.get("/", follow_redirects=False)
        
        # Assert
        assert response.status_code in [307, 308]
        assert "/static/index.html" in response.headers["location"]
    
    def test_root_redirect_follows(self, client):
        """
        Test: Following redirect from / to index.html
        
        Arrange: Test client ready
        Act: GET request to / with follow_redirects=True
        Assert: Verify final response is HTML (200 or follows redirect)
        """
        # Act
        response = client.get("/", follow_redirects=True)
        
        # Assert - The redirect should work
        assert response.status_code == 200


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_email_with_special_characters_encoded(self, client, fresh_activities):
        """
        Test: Email addresses with special characters are handled correctly
        
        Arrange: Email with + sign (valid email)
        Act: Sign up with special character email
        Assert: Verify signup succeeds and email is preserved
        """
        # Act
        response = client.post(
            "/activities/Programming Class/signup?email=test%2Balias@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
        activities_data = client.get("/activities").json()
        assert "test+alias@test.edu" in activities_data["Programming Class"]["participants"]
    
    def test_activity_name_with_spaces_encoded(self, client, fresh_activities):
        """
        Test: Activity names with spaces are handled correctly
        
        Arrange: Programming Class has spaces in name
        Act: Sign up for activity with spaces (URL encoded)
        Assert: Verify request succeeds
        """
        # Act
        response = client.post(
            "/activities/Programming%20Class/signup?email=ivy@test.edu"
        )
        
        # Assert
        assert response.status_code == 200
    
    def test_sequential_signups_and_unregisters(self, client, fresh_activities):
        """
        Test: Multiple sequential operations maintain correct state
        
        Arrange: Programming Class is empty
        Act: Sign up 3 people, unregister 1, sign up another
        Assert: Verify final state is correct
        """
        # Act - Sign up multiple people
        client.post("/activities/Programming Class/signup?email=jack@test.edu")
        client.post("/activities/Programming Class/signup?email=kate@test.edu")
        
        # Verify count
        response = client.get("/activities")
        assert len(response.json()["Programming Class"]["participants"]) == 2
        
        # Unregister one
        client.delete("/activities/Programming Class/unregister?email=jack@test.edu")
        
        # Verify count decreased
        response = client.get("/activities")
        assert len(response.json()["Programming Class"]["participants"]) == 1
        assert "kate@test.edu" in response.json()["Programming Class"]["participants"]
        assert "jack@test.edu" not in response.json()["Programming Class"]["participants"]
