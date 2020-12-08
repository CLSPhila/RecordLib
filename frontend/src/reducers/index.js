import { combineReducers } from "redux";

import sourceRecordsReducer from "./sourceRecords";
import ujsSearchReducer from "./ujsSearch";
import serviceAgencyReducer from "./serviceAgencies";
import cRecordReducer from "./crecord";
import attorneyReducer from "./attorney";
import userReducer from "./user";
import applicantReducer from "./applicant";
import analysisReducer from "./analysis";
import petitionsReducer from "./petitions";
import gradePredictionReducer from "./grades";
import messageReducer from "./messages";
import templatesReducer from "./petitionTemplates";

const rootReducer = combineReducers({
  user: userReducer, // the current user.
  applicantInfo: applicantReducer, // the subject of petitions to be generated.
  crecord: cRecordReducer, // a representation of a person's criminal record.
  analysis: analysisReducer, // the server's analysis of what petitions may be generated, and why
  petitions: petitionsReducer, // petitions that could be sent to the server to generate downloadable documents.
  sourceRecords: sourceRecordsReducer, // records the user has told the server they want to use for this session.
  attorney: attorneyReducer, // attorney information is entered into generated petitions.
  serviceAgencies: serviceAgencyReducer, // petitions can include a list of agencies that will receive service
  ujsSearchResults: ujsSearchReducer, //  results from searching the public ujs portal.
  gradePredictions: gradePredictionReducer, // results from guessing grades of charges
  message: messageReducer, // messages for user.
  templates: templatesReducer,  // Template documents for generating petitions. 
});

export default rootReducer;
