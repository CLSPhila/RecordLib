import React, { useState } from "react";
import { Petition } from "./Petition";

import { makeStyles } from "@material-ui/core/styles";
import blueGrey from "@material-ui/core/colors/blueGrey";
import { IconButton, Collapse } from "@material-ui/core";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";

const useStyles = makeStyles((theme) => {
  return {
    root: {
      border: "1px solid" + blueGrey[500],
      backgroundColor: blueGrey[50],
      padding: "1em",
      paddingBotton: "2em",
      marginBottom: "1em",
    },
    h2: {
      fontSize: "1.5em",
    },
    expand: {
      transform: "rotate(0deg)",
      marginLeft: "auto",
      transition: theme.transitions.create("transform", {
        duration: theme.transitions.duration.shortest,
      }),
    },
    expandOpen: {
      transform: "rotate(180deg)",
    },
  };
});

/**
 * Component to display a Decision about filtering cases from a CRecord.
 *
 *
 *
 * A Petition decision has three properties
 * - .name is the name of the rule that created the decision.
 * - .value is a list of Petitions.
 * - .reasoning is a list of Decisions that explain the petions that can be generated here.
 * - .type identifies this decision as a Filter decision  (and not, for example, a Petition Decision.)
 */
function FilterDecision(props) {
  const { decision } = props;
  const classes = useStyles();

  const [isExpanded, setIsExpanded] = useState(false);

  const clickExpandHandler = (e) => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className={classes.root}>
      <h2 className={classes.h2}>
        {" "}
        Cases and charges filtered with the rule, "{decision.name}"{" "}
      </h2>
      {decision.value.length > 0 ? (
        <p>
          This rule removed charges from {decision.value.length} cases, and did
          not consider them for expungement or sealing.{" "}
        </p>
      ) : (
        <p>
          This rule did not remove any cases or charges from consideration.{" "}
        </p>
      )}
      <div>
        <IconButton
          className={isExpanded ? classes.expandOpen : classes.expand}
          onClick={clickExpandHandler}
        >
          <ExpandMoreIcon />
        </IconButton>
        {!isExpanded ? (
          <span> See the detailed analysis of this rule. </span>
        ) : (
          <span> Hide details </span>
        )}
        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
          <pre>{JSON.stringify(decision.reasoning, null, 2)}</pre>
        </Collapse>
      </div>
    </div>
  );
}

export default FilterDecision;
