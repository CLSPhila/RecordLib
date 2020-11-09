import * as api from "../api";
import { upsertSourceRecords } from "./sourceRecords";
import { updateCRecord } from "./crecord";
import { newMessage } from "./messages";
/**
 * Actions related to accessing ujs-related api endpoints.
 *
 * (UJS is the public website of the PA criminal courts)
 */
export const SEARCH_UJS_BY_NAME_STATUS = "SEARCH_UJS_BY_NAME_STATUS";
export const SEARCH_UJS_BY_NAME_SUCCESS = "SEARCH_UJS_BY_NAME_SUCCESS";
export const UPLOAD_UJS_DOCS_PENDING = "UPLOAD_UJS_DOCS_PENDING";
export const UPLOAD_UJS_DOCS_FINISHED = "UPLOAD_UJS_DOCS_FINISHED";
export const TOGGLE_UJS_SELECTED_SEARCH_CASES =
  "TOGGLE_UJS_SELECTED_SEARCH_CASES";

function searchUSJByNameStatus(newStatus) {
  return {
    type: SEARCH_UJS_BY_NAME_STATUS,
    payload: newStatus,
  };
}

function searchUSJByNameSuccess({ searchResults }) {
  return {
    type: SEARCH_UJS_BY_NAME_SUCCESS,
    payload: searchResults,
  };
}

export function searchUJSByName(first_name, last_name, date_of_birth) {
  return (dispatch) => {
    dispatch(searchUSJByNameStatus("Started"));
    api
      .searchUJSByName(first_name, last_name, date_of_birth)
      .then((response) => {
        const data = response.data;
        if (data.errors && data.errors.length > 0 || !data.searchResults) {
          dispatch(searchUSJByNameStatus("error"));
        } else {
          dispatch(searchUSJByNameSuccess(data));
          dispatch(searchUSJByNameStatus("Success"));
        }
      })
      .catch((err) => {
        console.log("Searching ujs by name failed.");
        console.log(err);
        dispatch(newMessage(err));
      });
  };
}

export function toggleSelectedUJSSearchCases(docType, docNum, newValue = null) {
  /**
   * docType: either summary or docket
   * docNum: the number of the docket.
   */
  return {
    type: TOGGLE_UJS_SELECTED_SEARCH_CASES,
    payload: { docType, docNum, newValue },
  };
}

function uploadUJSDocsPending() {
  return {
    type: UPLOAD_UJS_DOCS_PENDING,
  };
}

function uploadUJSDocsFinished() {
  return {
    type: UPLOAD_UJS_DOCS_FINISHED,
  };
}

/**
 * Expand a set of search results from UJS into separate records
 * for Dockets and Summaries.
 *
 * Like [(docket, summary)] -> {dockets: [docket], summaries: [summary]}
 * @param {*} results
 */
function expandSearchResults(resultIds, cases) {
  const docketsToSend = resultIds
    .map((cId) => {
      const c = cases[cId];
      if (c.docketSelected) {
        return {
          caption: c.caption,
          docket_num: c.docket_number,
          court: c.court,
          url: c.docket_sheet_url,
          record_type: "DOCKET_PDF",
        };
      } else {
        return null;
      }
    })
    .filter((i) => i !== null);
  const summariesToSend = resultIds
    .map((cId) => {
      const c = cases[cId];
      if (c.summarySelected) {
        return {
          caption: c.caption,
          docket_num: c.docket_number,
          court: c.court,
          url: c.summary_url,
          record_type: "SUMMARY_PDF",
        };
      } else {
        return null;
      }
    })
    .filter((i) => i !== null);

  return { docketsToSend, summariesToSend };
}

export function uploadUJSDocs() {
  /**
   * A Thunk for sending the information about selected ujs search results to the
   * server and creating SourceRecords for them.
   *
   * The server will create SourceRecords for each, and return objects describing
   * these SoureRecords.
   *
   * Note that each UJS Search result describes two documents. One is a 'docket', and
   * the other is a 'summary'.
   *
   * In this action, we expand these search results, and send them to the server as separate records.
   *
   * Once the server responds with information identifying each new SourceRecord,
   * we'll also send the action to update the current crecord with the server and the
   * current set of sourcerecords.
   *
   * cases.result: a list of docket numbers
   * cases.entities: a object. keys are docket numbers, and values are info about
   *      a case, including docket number, summary and docket urls, and whether those
   *      things are selected.
   */

  return (dispatch, getState) => {
    dispatch(uploadUJSDocsPending());
    const cases = getState().ujsSearchResults.casesFound;
    const { docketsToSend, summariesToSend } = expandSearchResults(
      cases.result,
      cases.entities
    );
    const recordsToSend = docketsToSend.concat(summariesToSend);
    return api
      .uploadUJSDocs(recordsToSend)
      .then((response) => {
        const data = response.data;
        return dispatch(upsertSourceRecords(data));
      })
      .then(() => {
        return dispatch(updateCRecord());
      })
      .then(() => {
        //trying to force this to run after updateCRecord.
        return dispatch(uploadUJSDocsFinished());
      })
      .catch((err) => {
        console.log(err);
        return dispatch(uploadUJSDocsFinished());
      });
  };
}
