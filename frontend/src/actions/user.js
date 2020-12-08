import * as api from "../api";
import { newMessage } from "./messages";
import { UPDATE_PETITION } from "./petitions";
export const FETCH_USER_PROFILE_SUCCEEDED = "FETCH_USER_PROFILE_SUCCEEDED";
export const UPDATE_USER_PROFILE = "UPDATE_USER_PROFILE";

export function fetchUserProfileSucceeded(profileData) {
  return {
    type: FETCH_USER_PROFILE_SUCCEEDED,
    payload: profileData,
  };
}

export const updateUserProfile = (field, newValue) => {
  return {
    type: UPDATE_USER_PROFILE,
    payload: { [field]: newValue },
  };
};

export function fetchUserProfile() {
  return (dispatch) => {
    return api
      .fetchUserProfileData()
      .then((response) => {
        const data = response.data;
        console.log("returning dispatch of fetchUserProfileSucceeded`.");
        return dispatch(fetchUserProfileSucceeded(data));
      })
      .catch((err) => {
        return dispatch(newMessage({ msgText: err, severity: "error" }));
      });
  };
}

/**
 * Create a thunk to POST a modified user profile to the server.
 */
export function saveUserProfile(user) {
  return (dispatch) => {
    api
      .saveUserProfile(user)
      .then((response) => {
        return dispatch(
          newMessage({ msgText: "User info updated.", severity: "success" })
        );
      })
      .catch((err) => {
        return dispatch(newMessage({ msgText: err, severity: "error" }));
      });
  };
}
