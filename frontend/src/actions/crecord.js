import * as api from "../api";
import { merge } from "lodash";
import {
  normalizeCRecord,
  denormalizeCRecord,
  CRECORD_ID,
  normalizeAnalysis,
  denormalizeSourceRecords,
} from "../normalize";
import { updateAttorney } from "./index";
import { addOrReplaceApplicant } from "./applicant";
import { fetchUserProfile } from "./user";
import { upsertSourceRecords } from "./sourceRecords";
import { newPetition } from "./petitions";
import { newMessage } from "./messages";
export const UPDATE_CRECORD = "UPDATE_CRECORD";
export const UPDATE_CRECORD_SUCCEEDED = "UPDATE_CRECORD_SUCCEEDED";
export const FETCH_CRECORD_SUCCEEDED = "FETCH_CRECORD_SUCCEEDED";
export const ANALYZE_CRECORD_SUCCEEDED = "ANALYZE_CRECORD_SUCCEDED";

function analyzeRecordsSucceeded(analysis) {
  // normalizeAnalysis just pulls out the petitions that the analysis thinks can be generated, 
  // and makes them their own key in the payload of this action.
  const normalizedAnalysis = normalizeAnalysis(analysis);
  return {
    type: ANALYZE_CRECORD_SUCCEEDED,
    payload: normalizedAnalysis,
  };
}

const populateDefaultAtty = (dispatch, getState) => {
  return dispatch(fetchUserProfile())
    .then(() => {
      const user = getState().user;
      const defaultAtty = {
        address: {
          line_one: user.default_atty_address_line_one,
          city_state_zip: user.default_atty_address_line_two,
        },
        full_name: user.default_atty_name,
        organization: user.default_atty_organization,
        organization_phone: user.default_atty_phone,
        bar_id: user.default_bar_id,
      };
      return dispatch(updateAttorney(defaultAtty));
    })
    .catch((err) => {
      return err;
    });
};

/**
 * Create a thunk to send the CRecord to the server and receive an analysis of petitions that can be generated from this analysis,
 */
export function analyzeCRecord() {
  return (dispatch, getState) => {
    console.log("analyzing crecord");
    const crecord = getState().crecord;
    // initialize attorney to default if necessary
    const attorney = getState().attorney;
    if (!attorney.hasBeenEdited) {
      populateDefaultAtty(dispatch, getState);
    }
    const normalizedData = { entities: crecord, result: CRECORD_ID };
    const denormalizedCRecord = denormalizeCRecord(normalizedData);
    const applicantInfo = getState().applicantInfo;
    const person = Object.assign({}, applicantInfo.applicant, {
      aliases: applicantInfo.applicant.aliases.map(
        (aliasId) => applicantInfo.aliases[aliasId]
      ),
    });
    if (person.date_of_death === "") {
      delete person.date_of_death;
    }
    denormalizedCRecord["person"] = person;
    return api
      .analyzeCRecord(denormalizedCRecord)
      .then((response) => {
        const analysis = response.data;
        const action = analyzeRecordsSucceeded(analysis);
        dispatch(action);
        console.log(analysis);

        const atty = getState().attorney;

        const defaultIFPMessage = `${
          atty.organization || "____"
        } is a non-profit legal services organization that provides free legal assistance to low-income individuals. I, ${
          atty.full_name
        }, attorney for the Petitioner, certify that Petitioner meets the financial eligibility standards for representation by ${
          atty.organization
        } and that I am providing free legal service to Petitioner.`;

        // Go through the analysis from the server. Each element is a Decision.
        // For each Decision that describes Petitions to create (i.e., PetitionDecisions),
        // dispatch an action to create that Petition in State.
        analysis.decisions.forEach((decision) =>
          decision.type === "Petition"
            ? decision.value.forEach((petition) => {
                dispatch(
                  newPetition(
                    merge({}, petition, {
                      attorney: atty,
                      ifp_message: defaultIFPMessage,
                    })
                  )
                );
              })
            : null
        );
      })
      .catch((err) => {
        console.log("Error analyzing crecord.");
        console.log(err);
      });
  };
}

/**
 *
 * N.B. this action will trigger two reducers - one to update the crecord object that stores cases and charges, and one to update the 'applicant' slice.
 * @param {*} newCRecord
 */

export function updateCRecordSucceeded(newCRecord) {
  const normalizedCRecord = normalizeCRecord(newCRecord);
  return {
    type: UPDATE_CRECORD_SUCCEEDED,
    payload: { person: newCRecord.person, cRecord: normalizedCRecord },
  };
}

export function updateCRecord() {
  /**
   * Send the CRecord and SourceRecords to the server. the server will analyze the sourceRecord and integrate them into the
   * CRecord, and return a new crecord.
   */
  return (dispatch, getState) => {
    const crecord = getState().crecord;
    const sourceRecords = denormalizeSourceRecords(getState().sourceRecords);
    const normalizedData = { entities: crecord, result: CRECORD_ID };
    const denormalizedCRecord = denormalizeCRecord(normalizedData);
    const applicantInfo = getState().applicantInfo;
    const person = Object.assign({}, applicantInfo.applicant, {
      aliases: applicantInfo.applicant.aliases.map(
        (aliasId) => applicantInfo.aliases[aliasId]
      ),
    });
    delete person.editing;
    if (person.date_of_death === "") {
      delete person.date_of_death;
    }
    if (person.date_of_birth === "") {
      delete person.date_of_birth;
    }
    denormalizedCRecord["person"] = person;
    return api
      .integrateDocsWithRecord(denormalizedCRecord, sourceRecords)
      .then((response) => {
        // this function is not getting run until much later...
        // its getting added to the task queue, but not run til
        //
        dispatch(updateCRecordSucceeded(response.data.crecord));

        dispatch(addOrReplaceApplicant(response.data.crecord.person));
        return dispatch(
          upsertSourceRecords({
            source_records: response.data.source_records,
          })
        );
      })
      .catch((err) => {
        return dispatch(newMessage({ msgText: err, severity: "error" }));
      });
  };
}
