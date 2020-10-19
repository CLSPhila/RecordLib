import React, { useState } from "react";
import { connect } from "react-redux";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import TextAreaAutosize from "@material-ui/core/TextareaAutosize";
import InputLabel from "@material-ui/core/InputLabel";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import {
  updatePetition,
  setPetitionToEdit,
  newCaseForPetition,
  setServiceAgenciesOnPetition,
} from "frontend/src/actions/petitions";
import { pickBy, pick } from "lodash";
import { makeStyles } from "@material-ui/core/styles";

const useStyles = makeStyles((theme) => {
  return {
    root: {
      input: {
        paddingRight: theme.spacing(2),
      },
    },
    textArea: {
      width: "80%",
    },
  };
});

/**
 * Form for adding a new petition
 */
export const EditPetitionForm = (props) => {
  const {
    petition = {},
    petitionCases, // obj of cases attached to this petition.
    petitionCaseIds, // convenience list of ids of cases attached to this petition.
    cases,
    charges,
    setPetitionType,
    setOrganization,
    setAttorneyName,
    setStreetAddress,
    setCity,
    setPhone,
    setBarId,
    setIFPMessage,
    setCrimHistReport,
    setExpungementReasons,
    addCaseToPetition,
    setDoneEditing,
    setServiceAgenciesOnPetition,
    updateApplicant,
    updateApplicantAddress,
  } = props;

  const {
    id,
    attorney = {},
    petition_type,
    ifp_message,
    include_crim_hist_report,
    expungement_reasons,
    client = {},
  } = petition;

  const classes = useStyles();

  const { aliases = [] } = client;
  // All the cases in the CRecord, so the user
  // can pick which ones to add to petitions.
  const caseIds = cases ? Object.keys(cases) : [];

  const [newCaseDocketNumber, setNewCaseDocketNumber] = useState("");
  const [newServiceAgency, setNewServiceAgency] = useState("");

  // State hook to control the value of the new docket number to be added to this petition.
  const handleNewCaseDocketNumChange = (e) => {
    setNewCaseDocketNumber(e.target.value);
  };

  const handleEditNewServiceAgency = (e) => {
    setNewServiceAgency(e.target.value);
  };

  const handleAddNewServiceAgency = (e) => {
    e.preventDefault();
    const newServiceAgencies = petition.service_agencies
      ? Array.from(new Set([...petition.service_agencies, newServiceAgency]))
      : [newServiceAgency];
    setServiceAgenciesOnPetition(newServiceAgencies);
  };

  const handleDeleteServiceAgency = (agencyToDelete) => {
    return (e) => {
      e.preventDefault();
      const newServiceAgencies = petition.service_agencies.filter((s) => {
        return s !== agencyToDelete;
      });
      setServiceAgenciesOnPetition(newServiceAgencies);
    };
  };

  // Dispatch action to copy a case from crecord into Petition state.
  const handleAddCaseToPetition = (e) => {
    e.preventDefault();
    const caseInfo = cases[newCaseDocketNumber];
    const chargesToAdd = pick(charges, caseInfo.charges);
    addCaseToPetition(newCaseDocketNumber, caseInfo, chargesToAdd);
    setNewCaseDocketNumber("");
  };

  const handleSetPetitionType = (e) => {
    setPetitionType(e.target.value);
  };

  const handleSetOrganization = (e) => {
    setOrganization(e.target.value);
  };

  const handleSetAttorneyName = (e) => {
    setAttorneyName(e.target.value);
  };

  const handleSetStreetAddress = (e) => {
    setStreetAddress(e.target.value);
  };

  const handleSetCity = (e) => {
    setCity(e.target.value);
  };

  const handleSetPhone = (e) => {
    setPhone(e.target.value);
  };

  const handleSetBarId = (e) => {
    setBarId(e.target.value);
  };

  const handleSetIFPMessage = (e) => {
    setIFPMessage(e.target.value);
  };

  const handleSetCrimHistReport = (e) => {
    setCrimHistReport(e.target.value);
  };

  const handleSetExpungementReasons = (e) => {
    setExpungementReasons(e.target.value);
  };

  const handleDoneEditing = (e) => {
    setDoneEditing();
  };

  /** Create a function to handle updates to the applicant info. */
  const handleSetApplicant = (field) => {
    return (e) => {
      updateApplicant(field, e.target.value);
    };
  };

  /** Create a function to handle updates to the applicant info. */
  const handleSetApplicantAddress = (field) => {
    return (e) => {
      updateApplicantAddress(field, e.target.value);
    };
  };

  return (
    <form id={`edit-petition-${id}`} className={classes.root}>
      <h3>
        Edit Petition <b>{id}</b>
      </h3>
      <div>
        <InputLabel id="petition-type">Petition Type</InputLabel>
        <Select
          labelId="petition-type"
          id="select-petition-type"
          value={petition_type}
          onChange={handleSetPetitionType}
        >
          <MenuItem value={"Expungement"}>Expungement</MenuItem>
          <MenuItem value={"Sealing"}>Sealing</MenuItem>
        </Select>
      </div>
      <h4>Client</h4>
      <div>
        <TextField
          label="First Name"
          value={client.first_name}
          onChange={handleSetApplicant("first_name")}
          required
        ></TextField>
        <TextField
          required
          label="Last Name"
          value={client.last_name}
          onChange={handleSetApplicant("last_name")}
        ></TextField>
        <TextField
          required
          label="Date of birth"
          type="date"
          value={client.date_of_birth || ""}
          InputLabelProps={{ shrink: true }}
          onChange={handleSetApplicant("date_of_birth")}
        ></TextField>
        <TextField
          label="Date of death"
          value={client.date_of_death || ""}
          type="date"
          onChange={handleSetApplicant("date_of_death")}
          InputLabelProps={{ shrink: true }}
        ></TextField>
        <TextField
          label="SSN"
          value={client.ssn}
          onChange={handleSetApplicant("ssn")}
        ></TextField>
        <TextField
          label="Street address"
          value={client.address ? client.address.line_one : ""}
          onChange={handleSetApplicantAddress("line_one")}
        ></TextField>
        <TextField
          label="City/State/Zip"
          value={client.address ? client.address.city_state_zip : ""}
          onChange={handleSetApplicantAddress("city_state_zip")}
        ></TextField>
        <h5>Aliases</h5>
        <ul>
          {aliases.map((alias) => {
            return <li key={alias}>{alias}</li>;
          })}
        </ul>
      </div>
      <h4> Attorney</h4>
      <div>
        <div>
          <TextField
            label="Organization"
            value={attorney.organization}
            onChange={handleSetOrganization}
          />
          <TextField
            label="Full Name"
            value={attorney.full_name}
            onChange={handleSetAttorneyName}
          />
          <TextField
            label="Organization Address"
            value={attorney.address ? attorney.address.line_one : ""}
            onChange={handleSetStreetAddress}
          />
          <TextField
            label="Organization City/State/Zip"
            defaultValue={
              attorney.address ? attorney.address.city_state_zip : ""
            }
            onChange={handleSetCity}
          />
          <TextField
            label="Organization Phone"
            value={attorney.organization_phone || ""}
            onChange={handleSetPhone}
          />
          <TextField
            label="Bar ID number"
            value={attorney.bar_id || ""}
            onChange={handleSetBarId}
          />
        </div>
        <h4>Messages</h4>
        <div>
          <InputLabel htmlFor="ifp_message">IFP Message</InputLabel>
          <TextAreaAutosize
            id="ifp_message"
            label="IFP Message"
            value={ifp_message || ""}
            onChange={handleSetIFPMessage}
            className={classes.textArea}
          />
          <InputLabel htmlFor="include_crim_hist_report">
            Criminal History Report Message
          </InputLabel>
          <TextAreaAutosize
            id="include_crim_hist_report"
            label="Crim. Hist. report included message?"
            value={include_crim_hist_report || ""}
            onChange={handleSetCrimHistReport}
            className={classes.textArea}
          />
          <InputLabel htmlFor="expungement_reasons">
            Reasons for expungement
          </InputLabel>
          <TextAreaAutosize
            id="expungement_reasons"
            label="Expungement Reasons"
            value={expungement_reasons || ""}
            onChange={handleSetExpungementReasons}
            className={classes.textArea}
          />
        </div>
        <h4>Cases</h4>
        <div>
          <InputLabel id="case-select-label">
            Copy a case from the full record
          </InputLabel>
          <Select
            labelId="case-select-label"
            id="case-select"
            value={newCaseDocketNumber}
            onChange={handleNewCaseDocketNumChange}
          >
            {caseIds.map((caseId) => {
              return (
                <MenuItem key={caseId} value={caseId}>
                  {caseId}
                </MenuItem>
              );
            })}
          </Select>
          <Button
            onClick={handleAddCaseToPetition}
            disabled={newCaseDocketNumber === ""}
          >
            Add new case to petition
          </Button>
        </div>
        <div>
          <ul>
            {petitionCaseIds.map((pid) => {
              return (
                <li key={pid}>
                  Docket Number: {petitionCases[pid].docket_number}{" "}
                </li>
              );
            })}
          </ul>
        </div>
        <h4>Service Agencies</h4>
        <div>
          <TextField
            label="Service Agency"
            value={newServiceAgency}
            onChange={handleEditNewServiceAgency}
          ></TextField>
          <Button onClick={handleAddNewServiceAgency}>
            Add new service agency
          </Button>
          {petition.service_agencies ? (
            <ul>
              {petition.service_agencies.map((agency) => {
                return (
                  <li key={agency}>
                    {" "}
                    {agency}{" "}
                    <Button onClick={handleDeleteServiceAgency(agency)}>
                      Delete
                    </Button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <></>
          )}
        </div>
      </div>
      <Button type="submit" onClick={handleDoneEditing}>
        Done editing
      </Button>
    </form>
  );
};

const mapStateToProps = (state, ownProps) => {
  const { petitionId } = ownProps;
  const petition =
    state.petitions.petitionCollection.entities.petitions[petitionId];
  const petitionCaseIds = petition.cases || [];
  const petitionCases = pickBy(
    state.petitions.petitionCollection.entities.cases,
    (val, key) => {
      return petitionCaseIds.includes(key);
    }
  );
  const cases = state.crecord.cases;
  return {
    petition: petition,
    petitionCases: petitionCases,
    petitionCaseIds: petitionCaseIds,
    cases: cases,
    charges: state.crecord.charges,
    applicantInfo: state.applicantInfo,
  };
};

const mapDispatchToProps = (dispatch, ownProps) => {
  const { petitionId } = ownProps;
  return {
    setPetitionType: (newType) =>
      dispatch(updatePetition(petitionId, { petition_type: newType })),
    setOrganization: (newOrg) => {
      dispatch(
        updatePetition(petitionId, { attorney: { organization: newOrg } })
      );
    },
    setAttorneyName: (newName) => {
      dispatch(
        updatePetition(petitionId, { attorney: { full_name: newName } })
      );
    },
    setStreetAddress: (newAddress) => {
      dispatch(
        updatePetition(petitionId, {
          attorney: { address: { line_one: newAddress } },
        })
      );
    },
    setCity: (newCity) => {
      dispatch(
        updatePetition(petitionId, {
          attorney: { address: { city_state_zip: newCity } },
        })
      );
    },
    setPhone: (newPhone) => {
      dispatch(
        updatePetition(petitionId, {
          attorney: { organization_phone: newPhone },
        })
      );
    },
    setBarId: (barId) => {
      dispatch(updatePetition(petitionId, { attorney: { bar_id: barId } }));
    },
    setIFPMessage: (message) => {
      dispatch(updatePetition(petitionId, { ifp_message: message }));
    },
    setCrimHistReport: (message) => {
      dispatch(
        updatePetition(petitionId, { include_crim_hist_report: message })
      );
    },
    setExpungementReasons: (message) => {
      dispatch(updatePetition(petitionId, { expungement_reasons: message }));
    },
    updateApplicant: (field, value) => {
      dispatch(updatePetition(petitionId, { client: { [field]: value } }));
    },
    updateApplicantAddress: (field, value) => {
      dispatch(
        updatePetition(petitionId, { client: { address: { [field]: value } } })
      );
    },
    addCaseToPetition: (caseId, caseInfo, chargeInfo) => {
      dispatch(newCaseForPetition(petitionId, caseId, caseInfo, chargeInfo));
    },
    setServiceAgenciesOnPetition: (serviceAgencies) => {
      dispatch(setServiceAgenciesOnPetition(petitionId, serviceAgencies));
    },
    setDoneEditing: () => {
      dispatch(setPetitionToEdit(null));
    },
  };
};

export const EditPetitionFormConnected = connect(
  mapStateToProps,
  mapDispatchToProps
)(EditPetitionForm);
