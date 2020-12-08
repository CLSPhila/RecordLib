import React, { useEffect } from "react";
import Container from "@material-ui/core/Container";
import Paper from "@material-ui/core/Paper";
import CircularProgress from "@material-ui/core/CircularProgress";
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormControl from '@material-ui/core/FormControl';
import FormLabel from '@material-ui/core/FormLabel';
import RadioGroup from "@material-ui/core/RadioGroup"
import Radio from "@material-ui/core/Radio"
import Link from "@material-ui/core/Link"
import { connect } from "react-redux";
import {
  fetchUserProfile,
  updateUserProfile,
  saveUserProfile,
} from "../actions/user";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import Grid from "@material-ui/core/Grid";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
const useStyles = makeStyles((theme) => {
  return {
    paper: {
      marginTop: theme.spacing(5),
      padding: theme.spacing(2),
    },
  };
});

function EditUserProfile(props) {
  const {fetchUserProfile, updateUserProfile, saveUserProfile, user, templates } = props;
  const {
    username,
    email,
    first_name,
    last_name,
    default_atty_organization,
    default_atty_name,
    default_atty_address_line_one,
    default_atty_address_line_two,
    default_atty_phone,
    default_bar_id,
    expungement_petition_template,
    sealing_petition_template,
  } = user;
  const profileLoading = !username;
  const classes = useStyles();

  const { expungementTemplates, sealingTemplates } = templates


  const updateSealingPetitionTemplate = (e) => {
    updateUserProfile("sealing_petition_template", e.target.value)
  }

  const updateExpungementPetitionTemplate = (e) => {
    updateUserProfile("expungement_petition_template", e.target.value)
  }



  useEffect(() => {
    fetchUserProfile();
  }, []);

  const updateUser = (field) => {
    return (e) => {
      updateUserProfile(field, e.target.value);
    };
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    saveUserProfile(user);
  };

  return (
    <Container>
      <Paper className={classes.paper}>
        {profileLoading ? (
          <CircularProgress />
        ) : (
            <form>
          <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h3">{username}</Typography>
              </Grid>
              <Grid item xs={12} >
                <TextField
                  id="email"
                  label="Email Address"
                  required
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                  value={email || ""}
                  onChange={updateUser("email")}
                />
              </Grid>
              <Grid container item xs={12} direction="row">
                <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                  <TextField
                    id="first_name"
                    label="First Name"
                    value={first_name || ""}
                    onChange={updateUser("first_name")}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                  <TextField
                    id="last_name"
                    label="Last name"
                    value={last_name || ""}
                    onChange={updateUser("last_name")}
                  />
                </Grid>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h5">
                  Default Attorney information
                </Typography>
<Typography variant="body1">
                  Details of the attorney signing petitions you generate here.
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  id="default_atty_name"
                  label="Attorney Name"
                  value={default_atty_name || ""}
                  onChange={updateUser("default_atty_name")}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  id="default_atty_phone"
                  label="Attorney phone number"
                  value={default_atty_phone || ""}
                  onChange={updateUser("default_atty_phone")}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  id="default_bar_id"
                  label="Bar ID"
                  value={default_bar_id || ""}
                  onChange={updateUser("default_bar_id")}
                />
              </Grid>
 

              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  id="default_atty_organization"
                  label="Attorney Organization"
                  onChange={updateUser("default_atty_organization")}
                  value={default_atty_organization || ""}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  label="Organization Street Address"
                  id="default_atty_address_line_one"
                  value={default_atty_address_line_one || ""}
                  onChange={updateUser("default_atty_address_line_one")}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={6} lg={6} xl={6}>
                <TextField
                  label="Organization City/State/Zip"
                  id="default_atty_address_line_two"
                  value={default_atty_address_line_two || ""}
                  onChange={updateUser("default_atty_address_line_two")}
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h5">
                  Select Petition Templates
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <FormControl component="fieldset">
                  <FormLabel component="legend">Available Expungement Petition Templates</FormLabel>
                  <RadioGroup aria-label="expungement_petition_template" 
                    name="expungement_petition_template" 
                    value={expungement_petition_template || ""}
                    onChange={updateExpungementPetitionTemplate}>
                      {Object.keys(expungementTemplates).map(k => {
                        const template = expungementTemplates[k]
                        return(
                          <div key={template.id}>
                            <FormControlLabel value={template.id} control={<Radio />} label={template.name}/> 
                            <Link href={`/api/record/templates/expungement/${template.id}/`} target="__blank">(download)</Link>
                          </div>
                        )
                      })}
                  </RadioGroup>
                </FormControl>
              </Grid>
               <Grid item xs={12}>
                <FormControl component="fieldset">
                  <FormLabel component="legend">Available Sealing Petition Templates</FormLabel>
                  <RadioGroup aria-label="sealing_petition_template" 
                    name="sealing_petition_template" 
                    value={sealing_petition_template || ""}
                    onChange={updateSealingPetitionTemplate}>
                      {Object.keys(sealingTemplates).map(k => {
                        const template = sealingTemplates[k]
                        return(
                          <div key={template.id}>
                            <FormControlLabel value={template.id} control={<Radio />} label={template.name}/>
                            <Link href={`/api/record/templates/sealing/${template.id}/`} target="__blank">(download)</Link>
                          </div>
                        )
                      })}
                  </RadioGroup>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <Button onClick={handleSubmit}>Submit</Button>
              </Grid>
          </Grid>
            </form>
        )}
      </Paper>
    </Container>
  );
}

function mapStateToProps(state) {
  return {
    user: state.user,
    templates: state.templates,
  };
}

function mapDispatchToProps(dispatch) {
  return {
    fetchUserProfile: () => {
      dispatch(fetchUserProfile());
    },
    updateUserProfile: (field, newVal) => {
      dispatch(updateUserProfile(field, newVal));
    },
    saveUserProfile: (user) => {
      dispatch(saveUserProfile(user));
    },
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(EditUserProfile);
