import { CRECORD_ID } from "../normalize";
import { UPDATE_CRECORD_SUCCEEDED } from "../actions/crecord";

export const initialCrecordState = {
  charges: {},
  cases: {},
  sentences: {},
  cRecord: { [CRECORD_ID]: { cases: [] } },
};
/**
 * the crecord is a collection of cases, which each have 1 or more charges.
 * Charges, in turn, have 0 or more sentences.
 *
 * @param {} state
 * @param {*} action
 */
export default function cRecordReducer(state = initialCrecordState, action) {
  switch (action.type) {
    case UPDATE_CRECORD_SUCCEEDED: {
      const newCases = action.payload.cRecord.entities;
      const newState = {
        cRecord: {
          [CRECORD_ID]: Object.assign({}, state.cRecord[CRECORD_ID], {
            cases: newCases.cRecord[CRECORD_ID].cases, //state.cRecord[CRECORD_ID].cases.concat(
            //newCases.cRecord[CRECORD_ID].cases
            //), <-- overwrite new w/ old, not concat.
          }),
        },
        cases: Object.assign({}, newCases.cases), //state.cases, newCases.cases), <-- I think we want to just overwrite the crecord in state
        charges: Object.assign({}, newCases.charges), //state.charges, newCases.charges),     when we get a new crecord back from the server.
        sentences: Object.assign({}, newCases.sentences), //state.sentences, newCases.sentences),
      };
      return newState;
    }

    // Generic action to edit a field of any of the entities stored in state.
    // This case makes shallow copies so as to edit
    // the field while keeping state immutable.
    // TODO: consider using a library such as immutable.js for this and the next three cases.
    case "EDIT_ENTITY_VALUE": {
      const { entityName, entityId, field, value } = action.payload;

      const newState = Object.assign({}, state, {
        [entityName]: Object.assign({}, state[entityName], {
          [entityId]: Object.assign({}, state[entityName][entityId], {
            [field]: value,
          }),
        }),
      });

      return newState;
    }

    case "TOGGLE_EDITING": {
      const { caseId } = action.payload;

      const newState = Object.assign({}, state, {
        cases: Object.assign({}, state["cases"], {
          [caseId]: Object.assign({}, state["cases"][caseId], {
            editing: !state["cases"][caseId].editing,
          }),
        }),
      });

      return newState;
    }

    case "EDIT_SENTENCE_LENGTH": {
      const { sentenceId, field, value } = action.payload;

      const newState = Object.assign({}, state, {
        sentences: Object.assign({}, state["sentences"], {
          [sentenceId]: Object.assign({}, state["sentences"][sentenceId], {
            sentence_length: Object.assign(
              {},
              state["sentences"][sentenceId]["sentence_length"],
              {
                [field]: value,
              }
            ),
          }),
        }),
      });

      return newState;
    }

    case "ADD_ENTITY": {
      const {
        entityName,
        entity,
        parentId,
        parentEntityName,
        parentListKey,
      } = action.payload;

      const newState = Object.assign({}, state, {
        [entityName]: Object.assign({}, state[entityName], {
          [entity.id]: entity,
        }),
        [parentEntityName]: Object.assign({}, state[parentEntityName], {
          [parentId]: Object.assign({}, state[parentEntityName][parentId], {
            [parentListKey]: [
              ...state[parentEntityName][parentId][parentListKey],
              entity.id,
            ],
          }),
        }),
      });
      return newState;
    }

    default: {
      return state;
    }
  }
}
