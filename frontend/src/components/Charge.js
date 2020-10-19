import React from "react";
import PropTypes from "prop-types";

import Sentences from "./Sentences";

function Charge(props) {
  const { charge, gradePredictions } = props;

  const {
    id,
    offense,
    grade,
    statute,
    disposition,
    disposition_date,
    sequence,
    sentences,
  } = charge;
  const chargeStyle = {
    display: "grid",
    gridTemplateColumns: "450px 350px",
    margin: "15px",
    border: "1px solid black",
    borderRadius: "10px",
    padding: "10px",
    width: "820px",
  };

  return (
    <div className="charge" id={id} style={chargeStyle}>
      <div>Sequence Number: {sequence}</div>
      <div>Offense: {offense}</div>
      <div>Grade: {grade}</div>
      <div>Statute: {statute}</div>
      <div>Disposition: {disposition}</div>
      <div>Disposition Date: {disposition_date}</div>
      <Sentences sentences={sentences} chargeId={id} />
    </div>
  );
}

Charge.propTypes = {
  id: PropTypes.string,
  offense: PropTypes.string,
  grade: PropTypes.string,
  statute: PropTypes.string,
  disposition: PropTypes.string,
  disposition_date: PropTypes.string,
  sentences: PropTypes.array,
};

export default Charge;
