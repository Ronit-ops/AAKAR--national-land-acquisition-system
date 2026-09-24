import {

  useCallback,

  useEffect,

  useMemo,

  useState,

} from 'react';



import type { FormEvent } from 'react';



import {

  approveLandRequirement,

  createLandRequirement,

  getLandRequirement,

  listLandRequirements,

  listProjects,

  rejectLandRequirement,

  submitLandRequirement,

  updateLandRequirement,

  withdrawLandRequirement,

} from '../lib/api';



import type {

  LandRequirement,

  LandRequirementStatus,

} from '../types/landRequirements';



import type { Project } from '../types/projects';







const PAGE_SIZE = 10;



const LAND_REQUIREMENT_STATUSES: LandRequirementStatus[] = [

  'DRAFT',

  'SUBMITTED',

  'UNDER_REVIEW',

  'APPROVED',

  'REJECTED',

  'WITHDRAWN',

];





interface LandRequirementWorkspaceProps {

  permissions: ReadonlySet<string>;

}





interface LandRequirementFormValues {

  project_id: string;

  requirement_reference: string;

  purpose: string;

  required_area_sq_m: string;

  state: string;

  district: string;

  taluka: string;

  village: string;

  description: string;

}





const EMPTY_FORM: LandRequirementFormValues = {

  project_id: '',

  requirement_reference: '',

  purpose: '',

  required_area_sq_m: '',

  state: '',

  district: '',

  taluka: '',

  village: '',

  description: '',

};





function getErrorMessage(

  error: unknown,

  fallback: string,

): string {

  return error instanceof Error

    ? error.message

    : fallback;

}





function landRequirementText(key: string): string {
  const translations: Record<string, string> = {
  'eyebrow': 'LAND REQUIREMENT',
  'title': 'Land Requirement Management',
  'description': 'Define and manage the land area required for a project.',
  'create': 'Create Land Requirement',
  'new': 'New Land Requirement',
  'edit': 'Edit Land Requirement',
  'closeForm': 'Close',
  'project': 'Project',
  'selectProject': 'Select project',
  'loadingProjects': 'Loading projects...',
  'reference': 'Requirement Reference',
  'area': 'Required Area (sq. m)',
  'state': 'State',
  'district': 'District',
  'taluka': 'Taluka',
  'village': 'Village',
  'purpose': 'Purpose',
  'descriptionField': 'Description',
  'search': 'Search',
  'searchPlaceholder': 'Search by reference, purpose, district or village',
  'status': 'Status',
  'allStatuses': 'All statuses',
  'allProjects': 'All projects',
  'resetFilters': 'Reset filters',
  'records': 'records',
  'loading': 'Loading land requirements...',
  'loadingDescription': 'Fetching the latest land requirement records from AAKAR.',
  'noRecords': 'No land requirements found',
  'noRecordsDescription': 'Create a new land requirement or adjust the filters.',
  'details': 'Requirement Details',
  'location': 'Location',
  'created': 'Created',
  'updated': 'Updated',
  'squareMetres': 'sq. m',
  'noDescription': 'No description provided.',
  'selectRecord': 'Select a land requirement',
  'selectRecordDescription': 'Choose a record from the list to review its details and available actions.',
  'unknownProject': 'Unknown project',
  'previous': 'Previous',
  'next': 'Next',
  'cancel': 'Cancel',
  'saving': 'Saving...',
  'saveChanges': 'Save Changes',
  'processing': 'Processing...',
  'submit': 'Submit for Review',
  'approve': 'Approve',
  'reject': 'Reject',
  'withdraw': 'Withdraw',
  'actionReason': 'Review / action reason',
  'actionReasonPlaceholder': 'Enter a reason if rejecting...',
  'withdrawReason': 'Withdrawal reason',
  'withdrawReasonPlaceholder': 'Enter the reason for withdrawal...',
  'validationProject': 'Please select a project.',
  'validationReference': 'Requirement reference is required.',
  'validationReferenceLength': 'Requirement reference must be 80 characters or fewer.',
  'validationPurpose': 'Purpose is required.',
  'validationPurposeLength': 'Purpose must be 500 characters or fewer.',
  'validationArea': 'Required area must be a number greater than zero.',
  'validationState': 'State is required.',
  'validationDistrict': 'District is required.',
  'validationDescriptionLength': 'Description must be 5000 characters or fewer.',
  'loadError': 'Unable to load land requirements.',
  'projectsLoadError': 'Unable to load projects.',
  'detailError': 'Unable to load the selected land requirement.',
  'saveError': 'Unable to save the land requirement.',
  'createSuccess': 'Land requirement created successfully.',
  'updateSuccess': 'Land requirement updated successfully.',
  'submitSuccess': 'Land requirement submitted for review.',
  'approveSuccess': 'Land requirement approved successfully.',
  'rejectSuccess': 'Land requirement rejected.',
  'withdrawSuccess': 'Land requirement withdrawn.',
  'submitError': 'Unable to submit the land requirement.',
  'approveError': 'Unable to approve the land requirement.',
  'rejectError': 'Unable to reject the land requirement.',
  'withdrawError': 'Unable to withdraw the land requirement.',
  'rejectionReasonRequired': 'A rejection reason is required.',
  'withdrawReasonRequired': 'A withdrawal reason is required.',
  'approveConfirm': 'Approve this land requirement?',
  'withdrawConfirm': 'Withdraw this land requirement?',
  'statusDraft': 'Draft',
  'statusSubmitted': 'Submitted',
  'statusUnderReview': 'Under Review',
  'statusApproved': 'Approved',
  'statusRejected': 'Rejected',
  'statusWithdrawn': 'Withdrawn',
  'lifecycle': 'Workflow',
  'lifecycleDescription': 'Land requirements move through drafting, review, approval, rejection, and withdrawal under permission-controlled actions.'
  };

  const suffix = key.startsWith('landRequirement.')
    ? key.slice('landRequirement.'.length)
    : key;

  if (translations[suffix]) {
    return translations[suffix];
  }

  return suffix
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/^./, (character) => character.toUpperCase());
}


function formatStatus(

  status: LandRequirementStatus,

): string {

  switch (status) {

    case 'DRAFT':

      return landRequirementText('landRequirement.statusDraft');



    case 'SUBMITTED':

      return landRequirementText('landRequirement.statusSubmitted');



    case 'UNDER_REVIEW':

      return landRequirementText('landRequirement.statusUnderReview');



    case 'APPROVED':

      return landRequirementText('landRequirement.statusApproved');



    case 'REJECTED':

      return landRequirementText('landRequirement.statusRejected');



    case 'WITHDRAWN':

      return landRequirementText('landRequirement.statusWithdrawn');



    default:

      return status;

  }

}





function getStatusClass(

  status: LandRequirementStatus,

): string {

  switch (status) {

    case 'APPROVED':

      return 'land-requirement-status land-requirement-status-approved';



    case 'UNDER_REVIEW':

      return 'land-requirement-status land-requirement-status-review';



    case 'REJECTED':

      return 'land-requirement-status land-requirement-status-rejected';



    case 'WITHDRAWN':

      return 'land-requirement-status land-requirement-status-withdrawn';



    case 'SUBMITTED':

      return 'land-requirement-status land-requirement-status-submitted';



    case 'DRAFT':

    default:

      return 'land-requirement-status land-requirement-status-draft';

  }

}





function formatDateTime(

  value: string,

): string {

  const date = new Date(value);



  if (Number.isNaN(date.getTime())) {

    return 'Unavailable';

  }



  return date.toLocaleString();

}





function validateForm(

  values: LandRequirementFormValues,

  editing: boolean,

): string {

  if (!editing && !values.project_id) {

    return landRequirementText('landRequirement.validationProject');

  }



  if (!values.requirement_reference.trim()) {

    return landRequirementText('landRequirement.validationReference');

  }



  if (values.requirement_reference.trim().length > 80) {

    return landRequirementText('landRequirement.validationReferenceLength');

  }



  if (!values.purpose.trim()) {

    return landRequirementText('landRequirement.validationPurpose');

  }



  if (values.purpose.trim().length > 500) {

    return landRequirementText('landRequirement.validationPurposeLength');

  }



  const area = Number(values.required_area_sq_m);



  if (!Number.isFinite(area) || area <= 0) {

    return landRequirementText('landRequirement.validationArea');

  }



  if (!values.state.trim()) {

    return landRequirementText('landRequirement.validationState');

  }



  if (!values.district.trim()) {

    return landRequirementText('landRequirement.validationDistrict');

  }



  if (values.description.trim().length > 5000) {

    return landRequirementText('landRequirement.validationDescriptionLength');

  }



  return '';

}





export default function LandRequirementWorkspace({

  permissions,

}: LandRequirementWorkspaceProps) {



  const [requirements, setRequirements] = useState<

    LandRequirement[]

  >([]);



  const [projects, setProjects] = useState<Project[]>([]);



  const [selectedRequirementId, setSelectedRequirementId] =

    useState<string | null>(null);



  const [selectedRequirement, setSelectedRequirement] =

    useState<LandRequirement | null>(null);



  const [search, setSearch] = useState('');



  const [statusFilter, setStatusFilter] =

    useState<'all' | LandRequirementStatus>('all');



  const [projectFilter, setProjectFilter] =

    useState('');



  const [offset, setOffset] = useState(0);



  const [total, setTotal] = useState(0);



  const [loadingRequirements, setLoadingRequirements] =

    useState(true);



  const [loadingProjects, setLoadingProjects] =

    useState(true);



  const [requirementsError, setRequirementsError] =

    useState('');



  const [projectsError, setProjectsError] =

    useState('');



  const [showForm, setShowForm] = useState(false);



  const [editingRequirementId, setEditingRequirementId] =

    useState<string | null>(null);



  const [form, setForm] =

    useState<LandRequirementFormValues>(

      EMPTY_FORM,

    );



  const [formError, setFormError] = useState('');



  const [formSuccess, setFormSuccess] = useState('');



  const [savingForm, setSavingForm] = useState(false);



  const [changingStatus, setChangingStatus] =

    useState(false);



  const [actionReason, setActionReason] = useState('');



  const [showWithdrawReason, setShowWithdrawReason] = useState(false);



  const [actionError, setActionError] = useState('');



  const totalPages = Math.max(

    1,

    Math.ceil(total / PAGE_SIZE),

  );



  const currentPage =

    Math.floor(offset / PAGE_SIZE) + 1;



  const canCreate = permissions.has(

    'land_requirement.create',

  );



  const canUpdate = permissions.has(

    'land_requirement.update',

  );



  const canSubmit = permissions.has(

    'land_requirement.submit',

  );



  const canReview = permissions.has(

    'land_requirement.review',

  );



  const canWithdraw = permissions.has(

    'land_requirement.withdraw',

  );



  const projectMap = useMemo(

    () =>

      new Map(

        projects.map((project) => [

          project.id,

          project,

        ]),

      ),

    [projects],

  );



  const availableProjects = useMemo(

    () =>

      projects.filter(

        (project) => project.status !== 'CLOSED',

      ),

    [projects],

  );



  const loadProjects = useCallback(

    async () => {

      setLoadingProjects(true);

      setProjectsError('');



      try {

        const response = await listProjects({

          offset: 0,

          limit: 100,

        });



        setProjects(response.items);

      } catch (error) {

        setProjectsError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.projectsLoadError'),

          ),

        );

      } finally {

        setLoadingProjects(false);

      }

    },

    [],

  );



  const loadRequirements = useCallback(

    async () => {

      setLoadingRequirements(true);

      setRequirementsError('');



      try {

        const response =

          await listLandRequirements({

            search: search.trim() || undefined,

            status:

              statusFilter === 'all'

                ? undefined

                : statusFilter,

            project_id:

              projectFilter || undefined,

            offset,

            limit: PAGE_SIZE,

          });



        setRequirements(response.items);

        setTotal(response.total);



        if (

          selectedRequirementId &&

          !response.items.some(

            (item) =>

              item.id === selectedRequirementId,

          )

        ) {

          setSelectedRequirementId(null);

          setSelectedRequirement(null);

        }

      } catch (error) {

        setRequirementsError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.loadError'),

          ),

        );

      } finally {

        setLoadingRequirements(false);

      }

    },

    [

      offset,

      projectFilter,

      search,

      selectedRequirementId,

      statusFilter,



    ],

  );



  useEffect(() => {

    const timer = window.setTimeout(() => {

      void loadProjects();

    }, 0);



    return () => {

      window.clearTimeout(timer);

    };

  }, [loadProjects]);



  useEffect(() => {

    const timer = window.setTimeout(() => {

      void loadRequirements();

    }, 250);



    return () => {

      window.clearTimeout(timer);

    };

  }, [loadRequirements]);


  const resetFilters = () => {

    setSearch('');

    setStatusFilter('all');

    setProjectFilter('');

    setOffset(0);

    setSelectedRequirementId(null);

    setSelectedRequirement(null);

    setRequirementsError('');

    setActionError('');

    setFormError('');

    setFormSuccess('');

    setActionReason('');

    setShowWithdrawReason(false);

  };



  const resetForm = () => {

    setForm(EMPTY_FORM);

    setEditingRequirementId(null);

    setFormError('');

  };



  const openCreateForm = () => {

    resetForm();

    setFormSuccess('');

    setActionReason('');

    setShowWithdrawReason(false);

    setShowForm(true);

  };



  const openEditForm = (

    requirement: LandRequirement,

  ) => {

    setForm({

      project_id: requirement.project_id,

      requirement_reference:

        requirement.requirement_reference,

      purpose: requirement.purpose,

      required_area_sq_m:

        requirement.required_area_sq_m,

      state: requirement.state,

      district: requirement.district,

      taluka: requirement.taluka ?? '',

      village: requirement.village ?? '',

      description:

        requirement.description ?? '',

    });



    setEditingRequirementId(

      requirement.id,

    );



    setFormError('');

    setFormSuccess('');

    setActionReason('');

    setShowWithdrawReason(false);

    setShowForm(true);

  };



  const handleFormSubmit = async (

    event: FormEvent<HTMLFormElement>,

  ) => {

    event.preventDefault();



    const editing =

      editingRequirementId !== null;



    const validationError = validateForm(

      form,

      editing,

    );



    if (validationError) {

      setFormError(validationError);

      setFormSuccess('');

      return;

    }



    const area = Number(

      form.required_area_sq_m,

    );



    setSavingForm(true);

    setFormError('');

    setFormSuccess('');



    try {

      if (editingRequirementId) {

        const updated =

          await updateLandRequirement(

            editingRequirementId,

            {

              requirement_reference:

                form.requirement_reference.trim(),

              purpose:

                form.purpose.trim(),

              required_area_sq_m: area,

              state: form.state.trim(),

              district: form.district.trim(),

              taluka:

                form.taluka.trim() || null,

              village:

                form.village.trim() || null,

              description:

                form.description.trim() || null,

            },

          );



        setSelectedRequirement(updated);



        setRequirements((current) =>

          current.map((item) =>

            item.id === updated.id

              ? updated

              : item,

          ),

        );



        setFormSuccess(

          landRequirementText('landRequirement.updateSuccess'),

        );

      } else {

        const created =

          await createLandRequirement({

            project_id: form.project_id,

            requirement_reference:

              form.requirement_reference.trim(),

            purpose: form.purpose.trim(),

            required_area_sq_m: area,

            state: form.state.trim(),

            district: form.district.trim(),

            taluka:

              form.taluka.trim() || null,

            village:

              form.village.trim() || null,

            description:

              form.description.trim() || null,

          });



        setSelectedRequirement(created);

        setSelectedRequirementId(created.id);



        setRequirements((current) => [

          created,

          ...current.filter(

            (item) => item.id !== created.id,

          ),

        ]);



        setTotal((current) => current + 1);



        setFormSuccess(

          landRequirementText('landRequirement.createSuccess'),

        );

      }



      setShowForm(false);

      resetForm();

    } catch (error) {

      setFormError(

        getErrorMessage(

          error,

          landRequirementText('landRequirement.saveError'),

        ),

      );

    } finally {

      setSavingForm(false);

    }

  };



  const handleSelectRequirement =

    async (requirementId: string) => {

      setSelectedRequirementId(

        requirementId,

      );

      setSelectedRequirement(null);

      setRequirementsError('');

      setActionError('');

      setFormError('');

      setFormSuccess('');

      setActionReason('');

      setShowWithdrawReason(false);



      try {

        const requirement =

          await getLandRequirement(

            requirementId,

          );



        setSelectedRequirement(

          requirement,

        );

      } catch (error) {

        setRequirementsError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.detailError'),

          ),

        );

      }

    };



  const refreshSelectedRequirement =

    async () => {

      if (!selectedRequirementId) {

        return;

      }



      const requirement =

        await getLandRequirement(

          selectedRequirementId,

        );



      setSelectedRequirement(

        requirement,

      );



      setRequirements((current) =>

        current.map((item) =>

          item.id === requirement.id

            ? requirement

            : item,

        ),

      );

    };



  const handleSubmitRequirement =

    async () => {

      if (

        !selectedRequirement ||

        !canSubmit

      ) {

        return;

      }



      setChangingStatus(true);

      setActionError('');

      setFormSuccess('');



      try {

        await submitLandRequirement(

          selectedRequirement.id,

        );



        await refreshSelectedRequirement();



        setActionReason('');

        setShowWithdrawReason(false);

        setFormSuccess(

          landRequirementText('landRequirement.submitSuccess'),

        );

      } catch (error) {

        setActionError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.submitError'),

          ),

        );

      } finally {

        setChangingStatus(false);

      }

    };



  const handleApproveRequirement =

    async () => {

      if (

        !selectedRequirement ||

        !canReview

      ) {

        return;

      }



      const confirmed = window.confirm(

        landRequirementText('landRequirement.approveConfirm'),

      );



      if (!confirmed) {

        return;

      }



      setChangingStatus(true);

      setActionError('');

      setFormSuccess('');



      try {

        await approveLandRequirement(

          selectedRequirement.id,

        );



        await refreshSelectedRequirement();



        setActionReason('');

        setShowWithdrawReason(false);

        setFormSuccess(

          landRequirementText('landRequirement.approveSuccess'),

        );

      } catch (error) {

        setActionError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.approveError'),

          ),

        );

      } finally {

        setChangingStatus(false);

      }

    };



  const handleRejectRequirement =

    async () => {

      if (

        !selectedRequirement ||

        !canReview

      ) {

        return;

      }



      if (!actionReason.trim()) {

        setActionError(

          landRequirementText('landRequirement.rejectionReasonRequired'),

        );

        return;

      }



      setChangingStatus(true);

      setActionError('');

      setFormSuccess('');



      try {

        await rejectLandRequirement(

          selectedRequirement.id,

          {

            reason:

              actionReason.trim(),

          },

        );



        await refreshSelectedRequirement();

        setActionReason('');



        setFormSuccess(

          landRequirementText('landRequirement.rejectSuccess'),

        );

      } catch (error) {

        setActionError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.rejectError'),

          ),

        );

      } finally {

        setChangingStatus(false);

      }

    };



  const handleWithdrawRequirement =

    async () => {

      if (

        !selectedRequirement ||

        !canWithdraw

      ) {

        return;

      }



      if (!actionReason.trim()) {

        setActionError(

          landRequirementText('landRequirement.withdrawReasonRequired'),

        );

        return;

      }



      const confirmed = window.confirm(

        landRequirementText('landRequirement.withdrawConfirm'),

      );



      if (!confirmed) {

        return;

      }



      setChangingStatus(true);

      setActionError('');

      setFormSuccess('');



      try {

        await withdrawLandRequirement(

          selectedRequirement.id,

          {

            reason:

              actionReason.trim(),

          },

        );



        await refreshSelectedRequirement();

        setActionReason('');



        setFormSuccess(

          landRequirementText('landRequirement.withdrawSuccess'),

        );

      } catch (error) {

        setActionError(

          getErrorMessage(

            error,

            landRequirementText('landRequirement.withdrawError'),

          ),

        );

      } finally {

        setChangingStatus(false);

      }

    };



  const handleSearchChange = (

    value: string,

  ) => {

    setSearch(value);

    setOffset(0);

    setSelectedRequirementId(null);

    setSelectedRequirement(null);

  };



  const handleStatusFilterChange = (

    value:

      | 'all'

      | LandRequirementStatus,

  ) => {

    setStatusFilter(value);

    setOffset(0);

    setSelectedRequirementId(null);

    setSelectedRequirement(null);

  };



  const handleProjectFilterChange = (

    value: string,

  ) => {

    setProjectFilter(value);

    setOffset(0);

    setSelectedRequirementId(null);

    setSelectedRequirement(null);

  };



  return (

    <section className="management-shell">

      <div className="management-heading">

        <div>

          <p className="roles-eyebrow">

            {landRequirementText('landRequirement.eyebrow')}

          </p>



          <h1>

            {landRequirementText('landRequirement.title')}

          </h1>



          <p>

            {landRequirementText('landRequirement.description')}

          </p>

        </div>



        {canCreate && (

          <div className="management-actions">

            <button

              type="button"

              className="primary-button"

              onClick={openCreateForm}

              disabled={loadingProjects}

            >

              {landRequirementText('landRequirement.create')}

            </button>

          </div>

        )}

      </div>



      {projectsError && (

        <div

          className="error-message"

          role="alert"

        >

          {projectsError}

        </div>

      )}



      {requirementsError && (

        <div

          className="error-message"

          role="alert"

        >

          {requirementsError}

        </div>

      )}



      {showForm && (

        <form

          className="management-form-card"

          onSubmit={handleFormSubmit}

        >

          <div className="management-card-heading">

            <div>

              <p className="roles-eyebrow">

                {editingRequirementId

                  ? landRequirementText('landRequirement.edit')

                  : landRequirementText('landRequirement.new')}

              </p>



              <h2>

                {editingRequirementId

                  ? landRequirementText('landRequirement.edit')

                  : landRequirementText('landRequirement.create')}

              </h2>

            </div>



            <button

              type="button"

              className="ghost-button"

              onClick={() => {

                setShowForm(false);

                resetForm();

              }}

              disabled={savingForm}

            >

              {landRequirementText('landRequirement.closeForm')}

            </button>

          </div>



          <div className="management-form-grid">

            {!editingRequirementId && (

              <label>

                {landRequirementText('landRequirement.project')}



                <select

                  value={form.project_id}

                  onChange={(event) =>

                    setForm((current) => ({

                      ...current,

                      project_id:

                        event.target.value,

                    }))

                  }

                  required

                  disabled={

                    savingForm ||

                    loadingProjects

                  }

                >

                  <option value="">

                    {loadingProjects

                      ? landRequirementText('landRequirement.loadingProjects')

                      : landRequirementText('landRequirement.selectProject')}

                  </option>



                  {availableProjects.map(

                    (project) => (

                      <option

                        key={project.id}

                        value={project.id}

                      >

                        {project.code} —{' '}

                        {project.name}

                      </option>

                    ),

                  )}

                </select>

              </label>

            )}



            <label>

              {landRequirementText('landRequirement.reference')}



              <input

                type="text"

                value={

                  form.requirement_reference

                }

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    requirement_reference:

                      event.target.value,

                  }))

                }

                maxLength={80}

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {landRequirementText('landRequirement.area')}



              <input

                type="number"

                min="0.0001"

                step="0.0001"

                value={

                  form.required_area_sq_m

                }

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    required_area_sq_m:

                      event.target.value,

                  }))

                }

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {landRequirementText('landRequirement.state')}



              <input

                type="text"

                value={form.state}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    state: event.target.value,

                  }))

                }

                maxLength={100}

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {landRequirementText('landRequirement.district')}



              <input

                type="text"

                value={form.district}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    district:

                      event.target.value,

                  }))

                }

                maxLength={100}

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {landRequirementText('landRequirement.taluka')}



              <input

                type="text"

                value={form.taluka}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    taluka:

                      event.target.value,

                  }))

                }

                maxLength={100}

                disabled={savingForm}

              />

            </label>



            <label>

              {landRequirementText('landRequirement.village')}



              <input

                type="text"

                value={form.village}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    village:

                      event.target.value,

                  }))

                }

                maxLength={100}

                disabled={savingForm}

              />

            </label>



            <label className="management-form-full">

              {landRequirementText('landRequirement.purpose')}



              <input

                type="text"

                value={form.purpose}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    purpose:

                      event.target.value,

                  }))

                }

                maxLength={500}

                required

                disabled={savingForm}

              />

            </label>



            <label className="management-form-full">

              {landRequirementText('landRequirement.descriptionField')}



              <textarea

                value={form.description}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    description:

                      event.target.value,

                  }))

                }

                maxLength={5000}

                rows={5}

                disabled={savingForm}

              />

            </label>

          </div>



          {formError && (

            <div

              className="error-message"

              role="alert"

            >

              {formError}

            </div>

          )}



          {formSuccess && (

            <div

              className="success-message"

              role="status"

            >

              {formSuccess}

            </div>

          )}



          <div className="management-form-actions">

            <button

              type="submit"

              className="primary-button"

              disabled={savingForm}

            >

              {savingForm

                ? landRequirementText('landRequirement.saving')

                : editingRequirementId

                  ? landRequirementText('landRequirement.saveChanges')

                  : landRequirementText('landRequirement.create')}

            </button>



            <button

              type="button"

              className="secondary-button"

              disabled={savingForm}

              onClick={() => {

                setShowForm(false);

                resetForm();

              }}

            >

              {landRequirementText('landRequirement.cancel')}

            </button>

          </div>

        </form>

      )}



      <div className="management-layout">

        <section className="users-panel">

          <div className="users-toolbar">

            <div className="search-field">

              <label htmlFor="land-requirement-search">

                {landRequirementText('landRequirement.search')}

              </label>



              <input

                id="land-requirement-search"

                type="search"

                value={search}

                placeholder={landRequirementText('landRequirement.searchPlaceholder')}

                onChange={(event) =>

                  handleSearchChange(

                    event.target.value,

                  )

                }

              />

            </div>



            <div className="filter-field">

              <label htmlFor="land-requirement-status-filter">

                {landRequirementText('landRequirement.status')}

              </label>



              <select

                id="land-requirement-status-filter"

                value={statusFilter}

                onChange={(event) =>

                  handleStatusFilterChange(

                    event.target.value as

                      | 'all'

                      | LandRequirementStatus,

                  )

                }

              >

                <option value="all">

                  {landRequirementText('landRequirement.allStatuses')}

                </option>



                {LAND_REQUIREMENT_STATUSES.map(

                  (status) => (

                    <option

                      key={status}

                      value={status}

                    >

                      {formatStatus(

                        status)}

                    </option>

                  ),

                )}

              </select>

            </div>



            <div className="filter-field">

              <label htmlFor="land-requirement-project-filter">

                {landRequirementText('landRequirement.project')}

              </label>



              <select

                id="land-requirement-project-filter"

                value={projectFilter}

                onChange={(event) =>

                  handleProjectFilterChange(

                    event.target.value,

                  )

                }

              >

                <option value="">

                  {landRequirementText('landRequirement.allProjects')}

                </option>



                {projects.map((project) => (

                  <option

                    key={project.id}

                    value={project.id}

                  >

                    {project.code}

                  </option>

                ))}

              </select>

            </div>



            <button

              type="button"

              className="ghost-button"

              onClick={resetFilters}

              disabled={

                loadingRequirements ||

                (!search &&

                  statusFilter === 'all' &&

                  !projectFilter)

              }

            >

              {landRequirementText('landRequirement.resetFilters')}

            </button>

          </div>



          <div className="users-summary">

            <span>

              {total}{' '}

              {landRequirementText('landRequirement.records')}

            </span>



            <span>

              {currentPage} / {totalPages}

            </span>

          </div>



          {loadingRequirements ? (

            <div className="management-empty-state">

              <strong>

                {landRequirementText('landRequirement.loading')}

              </strong>



              <p>

                {landRequirementText('landRequirement.loadingDescription')}

              </p>

            </div>

          ) : requirements.length === 0 ? (

            <div className="management-empty-state">

              <strong>

                {landRequirementText('landRequirement.noRecords')}

              </strong>



              <p>

                {statusFilter !== 'all' || projectFilter || search

                  ? 'No records match the current filters. Reset filters to view all land requirements.'

                  : landRequirementText('landRequirement.noRecordsDescription')}

              </p>

            </div>

          ) : (

            <div className="user-list">

              {requirements.map(

                (requirement) => {

                  const project =

                    projectMap.get(

                      requirement.project_id,

                    );



                  const isSelected =

                    requirement.id ===

                    selectedRequirementId;



                  return (

                    <button

                      type="button"

                      key={requirement.id}

                      className={

                        isSelected

                          ? 'user-list-item user-list-item-active'

                          : 'user-list-item'

                      }

                      onClick={() => {

                        void handleSelectRequirement(

                          requirement.id,

                        );

                      }}

                    >

                      <span className="user-list-main">

                        <strong>

                          {

                            requirement.requirement_reference

                          }

                        </strong>



                        <span>

                          {project?.code ??

                            landRequirementText('landRequirement.unknownProject')}{' '}

                          ·{' '}

                          {requirement.district}

                        </span>

                      </span>



                      <span

                        className={getStatusClass(

                          requirement.status,

                        )}

                      >

                        {formatStatus(

                          requirement.status)}

                      </span>

                    </button>

                  );

                },

              )}

            </div>

          )}



          <div className="pagination-controls">

            <button

              type="button"

              className="ghost-button"

              disabled={

                offset === 0 ||

                loadingRequirements

              }

              onClick={() =>

                setOffset((currentOffset) =>

                  Math.max(

                    0,

                    currentOffset -

                      PAGE_SIZE,

                  ),

                )

              }

            >

              {landRequirementText('landRequirement.previous')}

            </button>



            <span>

              {currentPage} / {totalPages}

            </span>



            <button

              type="button"

              className="ghost-button"

              disabled={

                offset + PAGE_SIZE >=

                  total ||

                loadingRequirements ||

                total === 0

              }

              onClick={() =>

                setOffset(

                  (currentOffset) =>

                    currentOffset +

                    PAGE_SIZE,

                )

              }

            >

              {landRequirementText('landRequirement.next')}

            </button>

          </div>

        </section>



        <section className="detail-panel">

          {!selectedRequirement && (

            <div className="management-empty-state management-empty-state-large">

              <span className="detail-placeholder-icon">

                भूमि

              </span>



              <strong>

                {landRequirementText('landRequirement.selectRecord')}

              </strong>



              <p>

                {landRequirementText('landRequirement.selectRecordDescription')}

              </p>

            </div>

          )}



          {selectedRequirement && (

            <div className="profile-card">

              <div className="management-card-heading">

                <div>

                  <p className="roles-eyebrow">

                    {landRequirementText('landRequirement.details')}

                  </p>



                  <h2>

                    {

                      selectedRequirement.requirement_reference

                    }

                  </h2>



                  <p>

                    {projectMap.get(

                      selectedRequirement.project_id,

                    )?.name ??

                      landRequirementText('landRequirement.unknownProject')}

                  </p>

                </div>



                <span

                  className={getStatusClass(

                    selectedRequirement.status,

                  )}

                >

                  {formatStatus(

                    selectedRequirement.status)}

                </span>

              </div>



              <div className="profile-grid">

                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.project')}

                  </span>



                  <strong>

                    {projectMap.get(

                      selectedRequirement.project_id,

                    )?.code ??

                      landRequirementText('landRequirement.unknownProject')}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.reference')}

                  </span>



                  <strong>

                    {

                      selectedRequirement.requirement_reference

                    }

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.area')}

                  </span>



                  <strong>

                    {

                      selectedRequirement.required_area_sq_m

                    }{' '}

                    {landRequirementText('landRequirement.squareMetres')}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.location')}

                  </span>



                  <strong>

                    {[

                      selectedRequirement.village,

                      selectedRequirement.taluka,

                      selectedRequirement.district,

                      selectedRequirement.state,

                    ]

                      .filter(Boolean)

                      .join(', ')}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.created')}

                  </span>



                  <strong>

                    {formatDateTime(

                      selectedRequirement.created_at,

                    )}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {landRequirementText('landRequirement.updated')}

                  </span>



                  <strong>

                    {formatDateTime(

                      selectedRequirement.updated_at,

                    )}

                  </strong>

                </div>

              </div>



              <div className="profile-description">

                <span>

                  {landRequirementText('landRequirement.purpose')}

                </span>



                <p>

                  {

                    selectedRequirement.purpose

                  }

                </p>

              </div>



              <div className="profile-description">

                <span>

                  {landRequirementText('landRequirement.descriptionField')}

                </span>



                <p>

                  {selectedRequirement.description ||

                    landRequirementText('landRequirement.noDescription')}

                </p>

              </div>



              {actionError && (

                <div

                  className="error-message"

                  role="alert"

                >

                  {actionError}

                </div>

              )}



              {formSuccess && (

                <div

                  className="success-message"

                  role="status"

                >

                  {formSuccess}

                </div>

              )}



              <div className="management-form-actions">

                {canUpdate &&

                  (

                    selectedRequirement.status ===

                      'DRAFT' ||

                    selectedRequirement.status ===

                      'REJECTED'

                  ) && (

                    <button

                      type="button"

                      className="secondary-button"

                      onClick={() =>

                        openEditForm(

                          selectedRequirement,

                        )

                      }

                      disabled={changingStatus}

                    >

                      {landRequirementText('landRequirement.edit')}

                    </button>

                  )}



                {canSubmit &&

                  (

                    selectedRequirement.status ===

                      'DRAFT' ||

                    selectedRequirement.status ===

                      'REJECTED'

                  ) && (

                    <button

                      type="button"

                      className="primary-button"

                      onClick={() => {

                        void handleSubmitRequirement();

                      }}

                      disabled={changingStatus}

                    >

                      {changingStatus

                        ? landRequirementText('landRequirement.processing')

                        : landRequirementText('landRequirement.submit')}

                    </button>

                  )}



                {canReview &&

                  selectedRequirement.status ===

                    'UNDER_REVIEW' && (

                    <button

                      type="button"

                      className="primary-button"

                      onClick={() => {

                        void handleApproveRequirement();

                      }}

                      disabled={changingStatus}

                    >

                      {changingStatus

                        ? landRequirementText('landRequirement.processing')

                        : landRequirementText('landRequirement.approve')}

                    </button>

                  )}



                {canReview &&

                  selectedRequirement.status ===

                    'UNDER_REVIEW' && (

                    <button

                      type="button"

                      className="secondary-button"

                      onClick={() => {

                        void handleRejectRequirement();

                      }}

                      disabled={changingStatus}

                    >

                      {landRequirementText('landRequirement.reject')}

                    </button>

                  )}



                {canWithdraw &&

                  (

                    selectedRequirement.status ===

                      'DRAFT' ||

                    selectedRequirement.status ===

                      'UNDER_REVIEW' ||

                    selectedRequirement.status ===

                      'REJECTED'

                  ) && (

                    <button

                      type="button"

                      className="secondary-button"

                      onClick={() => {

                        setActionError('');

                        setFormSuccess('');

                        setActionReason('');

                        setShowWithdrawReason(

                          (current) => !current,

                        );

                      }}

                      disabled={changingStatus}

                    >

                      {showWithdrawReason

                        ? 'Cancel Withdrawal'

                        : landRequirementText('landRequirement.withdraw')}

                    </button>

                  )}

              </div>



              {canReview &&

                selectedRequirement.status ===

                  'UNDER_REVIEW' && (

                  <div
                    className="profile-description"
                    style={{
                      display: 'block',
                      width: '100%',
                      boxSizing: 'border-box',
                      marginTop: '14px',
                      padding: '14px 16px',
                      border: '1px solid #dce5dd',
                      borderRadius: '12px',
                      background: '#f8faf7',
                    }}
                  >
                    <span
                      style={{
                        display: 'block',
                        marginBottom: '8px',
                      }}
                    >
                      {landRequirementText('landRequirement.actionReason')}
                    </span>

                    <textarea
                      value={actionReason}
                      onChange={(event) =>
                        setActionReason(
                          event.target.value,
                        )
                      }
                      maxLength={2000}
                      rows={4}
                      placeholder={landRequirementText('landRequirement.actionReasonPlaceholder')}
                      disabled={changingStatus}
                      style={{
                        display: 'block',
                        width: '100%',
                        minWidth: 0,
                        boxSizing: 'border-box',
                        resize: 'vertical',
                        padding: '11px 12px',
                        border: '1px solid #d6dfd7',
                        borderRadius: '10px',
                        color: '#223127',
                        background: '#ffffff',
                        font: 'inherit',
                        fontSize: '13px',
                        lineHeight: 1.5,
                      }}
                    />
                  </div>

                )}



              {canWithdraw &&

                showWithdrawReason &&

                (

                  selectedRequirement.status ===

                    'DRAFT' ||

                  selectedRequirement.status ===

                    'UNDER_REVIEW' ||

                  selectedRequirement.status ===

                    'REJECTED'

                ) && (

                  <div

                    className="profile-description"

                    style={{

                      display: 'block',

                      width: '100%',

                      boxSizing: 'border-box',

                      marginTop: '14px',

                      padding: '14px 16px',

                      border: '1px solid #dce5dd',

                      borderRadius: '12px',

                      background: '#f8faf7',

                    }}

                  >

                    <span

                      style={{

                        display: 'block',

                        marginBottom: '8px',

                      }}

                    >

                      {landRequirementText('landRequirement.withdrawReason')}

                    </span>



                    <textarea

                      value={actionReason}

                      onChange={(event) =>

                        setActionReason(

                          event.target.value,

                        )

                      }

                      maxLength={2000}

                      rows={4}

                      placeholder={landRequirementText('landRequirement.withdrawReasonPlaceholder')}

                      disabled={changingStatus}

                      style={{

                        display: 'block',

                        width: '100%',

                        minWidth: 0,

                        boxSizing: 'border-box',

                        resize: 'vertical',

                        padding: '11px 12px',

                        border: '1px solid #d6dfd7',

                        borderRadius: '10px',

                        color: '#223127',

                        background: '#ffffff',

                        font: 'inherit',

                        fontSize: '13px',

                        lineHeight: 1.5,

                      }}

                    />

                    <div

                      className="management-form-actions"

                      style={{

                        justifyContent: 'flex-end',

                        marginTop: '12px',

                      }}

                    >

                      <button

                        type="button"

                        className="primary-button"

                        onClick={() => {

                          void handleWithdrawRequirement();

                        }}

                        disabled={

                          changingStatus ||

                          !actionReason.trim()

                        }

                      >

                        {changingStatus

                          ? landRequirementText('landRequirement.processing')

                          : 'Confirm Withdrawal'}

                      </button>

                    </div>

                  </div>

                )}

            </div>

          )}

        </section>

      </div>



      <div className="authorization-note">

        <span>

          {landRequirementText('landRequirement.lifecycle')}

        </span>



        <p>

          {landRequirementText('landRequirement.lifecycleDescription')}

        </p>

      </div>

    </section>

  );

}
