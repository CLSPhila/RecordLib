import React from "react";
import PropTypes from "prop-types";

import Charges from "./Charges";

function Case(props) {
  const {
    id,
    docket_number,
    otn,
    dc,
    status,
    county,
    judge,
    arrest_date,
    disposition_date,
    charges,
    total_fines,
    fines_paid,
    complaint_date,
    judge_address,
    affiant,
    arresting_agency,
    arresting_agency_address,
    related_cases,
    toggleEditing,
  } = props;
  const caseStyle = {
    display: "grid",
    gridTemplateColumns: "270px 270px 270px",
    margin: "10px",
    border: "1px solid black",
    borderRadius: "15px",
    padding: "10px",
    width: "860px",
  };

  return (
    <div className="case" id={id} style={caseStyle}>
      <div style={{ gridColumn: "1 / 3" }}>Docket Number: {docket_number}</div>
      <button
        type="button"
        style={{ marginLeft: "20px" }}
        onClick={toggleEditing}
      >
        Edit
      </button>
      <div>OTN: {otn}</div>
      <div>DC: {dc}</div>
      <div>Status: {status}</div>
      <div>County: {county}</div>
      <div>Judge: {judge}</div>
      <div>Judge Address: {judge_address}</div>
      <div>Arrest Date: {arrest_date}</div>
      <div>Disposition Date: {disposition_date}</div>
      <div>Total Fines: {total_fines}</div>
      <div>Fines Paid: {fines_paid}</div>
      <div>Complaint Date: {complaint_date}</div>
      <div>Affiant: {affiant}</div>
      <div>Arresting Agency: {arresting_agency}</div>
      <div>Arresting Agency Address: {arresting_agency_address}</div>
      <div></div>
      <div></div>
      <Charges caseId={id} charges={charges} editing={false} />
      {related_cases ? (
        <div>
          <div> Related Cases:</div>
          <ul>
            {related_cases.map((docket_num, idx) => {
              return <li key={idx}>{docket_num}</li>;
            })}
          </ul>
        </div>
      ) : (
        <></>
      )}
    </div>
  );
}

Case.propTypes = {
  id: PropTypes.string,
  docket_number: PropTypes.string,
  otn: PropTypes.string,
  dc: PropTypes.string,
  status: PropTypes.string,
  county: PropTypes.string,
  judge: PropTypes.string,
  arrest_date: PropTypes.string,
  disposition_date: PropTypes.string,
  charges: PropTypes.array,
  total_fines: PropTypes.number,
  fines_paid: PropTypes.number,
  complaint_date: PropTypes.string,
  judge_address: PropTypes.string,
  affiant: PropTypes.string,
  arresting_agency: PropTypes.string,
  arresting_agency_address: PropTypes.string,
  related_cases: PropTypes.arrayOf(PropTypes.string),
  toggleEditing: PropTypes.func,
};

export default Case;
