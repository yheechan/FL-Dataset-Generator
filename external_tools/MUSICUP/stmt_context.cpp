#include "music_utility.h"
#include "stmt_context.h"

StmtContext::StmtContext(CompilerInstance *CI)
	:proteumstyle_stmt_start_line_num_(0),
	is_inside_stmtexpr_(false), is_inside_array_decl_size_(0),
	is_inside_enumdecl_(false), last_return_statement_line_num_(0),
	is_assigned_to_special_(false), is_lambda_inside_declstmt_(false),
	is_constexpr_(false), is_enumclasstype_(false),
	is_casevalue_(false)
{
	clang::SourceManager &src_mgr = CI->getSourceManager();
	clang::SourceLocation start_of_file = \
			src_mgr.getLocForStartOfFile(src_mgr.getMainFileID());

	lhs_of_assignment_range_ = new clang::SourceRange(
				start_of_file, start_of_file);
  rhs_of_special_assignment_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  Lambda_expr_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  decl_stmt_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  addressop_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  unary_inc_dec_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  fielddecl_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  currently_parsed_function_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  switchstmt_condition_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  case_value_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  arraysubscript_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  switchcase_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  non_floating_expr_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);
  typedef_range_ = new clang::SourceRange(
  			start_of_file, start_of_file);

  currently_parsed_function_name_ = "MUSIC_global";
}

int StmtContext::getProteumStyleLineNum()
{
	return proteumstyle_stmt_start_line_num_;
}

SourceRange* StmtContext::getLhsOfAssignmentRange()
{
	return lhs_of_assignment_range_;
}

void StmtContext::setProteumStyleLineNum(int num)
{
	proteumstyle_stmt_start_line_num_ = num;
}

void StmtContext::setIsInStmtExpr(bool value)
{
	is_inside_stmtexpr_ = value;
}

void StmtContext::setIsInArrayDeclSize(bool value)
{
	is_inside_array_decl_size_ = value;
}

void StmtContext::setIsInEnumDecl(bool value)
{
	is_inside_enumdecl_ = value;
}

void StmtContext::setIsEnumClass(bool value)
{
	is_enumclasstype_ = value;
}

void StmtContext::setIslambdaInDeclstmt(bool value)
{
	is_lambda_inside_declstmt_ = value;
}

void StmtContext::setIsInSpecialAssignment(bool value)
{
	is_assigned_to_special_ = value;
}

void StmtContext::setIsInConstExpr(bool value)
{
	is_constexpr_ = value;
}

void StmtContext::setRhsOfSpecialAssignmentRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (rhs_of_special_assignment_ != nullptr)
		delete rhs_of_special_assignment_;

	rhs_of_special_assignment_ = range;
}

void StmtContext::setLambdaExprRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (Lambda_expr_ != nullptr)
		delete Lambda_expr_;

	Lambda_expr_ = range;
}

void StmtContext::setDeclStmtRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (decl_stmt_ != nullptr)
		delete decl_stmt_;

	decl_stmt_ = range;
}

void StmtContext::setLhsOfAssignmentRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (lhs_of_assignment_range_ != nullptr)
		delete lhs_of_assignment_range_;

	lhs_of_assignment_range_ = range;
}

void StmtContext::setAddressOpRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (addressop_range_ != nullptr)
		delete addressop_range_;

	addressop_range_ = range;
}

void StmtContext::setUnaryIncrementDecrementRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (unary_inc_dec_range_ != nullptr)
		delete unary_inc_dec_range_;

	unary_inc_dec_range_ = range;
}

void StmtContext::setFieldDeclRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (fielddecl_range_ != nullptr)
		delete fielddecl_range_;

	fielddecl_range_ = range;
}

void StmtContext::setCurrentlyParsedFunctionRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (currently_parsed_function_range_ != nullptr)
		delete currently_parsed_function_range_;

	currently_parsed_function_range_ = range;
}

void StmtContext::setSwitchStmtConditionRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (switchstmt_condition_range_ != nullptr)
		delete switchstmt_condition_range_;

	switchstmt_condition_range_ = range;
}

void StmtContext::setCaseValueRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (switchstmt_condition_range_ != nullptr)
		delete switchstmt_condition_range_;

	switchstmt_condition_range_ = range;
}

void StmtContext::setArraySubscriptRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (arraysubscript_range_ != nullptr)
		delete arraysubscript_range_;

	arraysubscript_range_ = range;
}

void StmtContext::setSwitchCaseRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (switchcase_range_ != nullptr)
		delete switchcase_range_;

	switchcase_range_ = range;
}

void StmtContext::setNonFloatingExprRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (non_floating_expr_range_ != nullptr)
		delete non_floating_expr_range_;

	non_floating_expr_range_ = range;
}

void StmtContext::setTypedefDeclRange(clang::SourceRange *range)
{
	if (range == nullptr) return;

	if (typedef_range_ != nullptr)
		delete typedef_range_;

	typedef_range_ = range;
}

void StmtContext::setCurrentlyParsedFunctionName(std::string function_name)
{
  currently_parsed_function_name_ = function_name;
}

bool StmtContext::IsInStmtExpr()
{
	return is_inside_stmtexpr_;
}

bool StmtContext::IsInArrayDeclSize()
{
	return is_inside_array_decl_size_;
} 

bool StmtContext::IsInEnumDecl()
{
	return is_inside_enumdecl_;
}

bool StmtContext::IsEnumClassType()
{
	return is_enumclasstype_;
}

bool StmtContext::IsInLambda()
{
	return is_lambda_inside_declstmt_;
}

bool StmtContext::IsInConstExpr()
{
	return is_constexpr_;
}

bool StmtContext::IsInLhsOfAssignmentRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *lhs_of_assignment_range_);
}

bool StmtContext::IsInRhsOfSpecialAssignmentRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *rhs_of_special_assignment_);
}

bool StmtContext::IsInAddressOpRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *addressop_range_);
}

bool StmtContext::IsInUnaryIncrementDecrementRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *unary_inc_dec_range_);
}

bool StmtContext::IsInFieldDeclRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *fielddecl_range_);
}

bool StmtContext::IsInCurrentlyParsedFunctionRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), 
													 *currently_parsed_function_range_);
}

bool StmtContext::IsInSwitchStmtConditionRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *switchstmt_condition_range_);
}

bool StmtContext::IsInCaseValueRange(Expr *s)
{
	// if(!LocationBeforeRangeStart(s->getBeginLoc(), *case_value_range_)){
	// 	cout<<"cp1"<<endl;
	// }
	// if(!LocationAfterRangeEnd(s->getBeginLoc(), *case_value_range_)){
	// 	cout<<"cp2"<<endl;
	// }
	// if(s->getBeginLoc() != (*case_value_range_).getEnd()){

	// 	cout<<"cppp1"<<endl;
	// }
	// if(!(s->getBeginLoc() < (*case_value_range_).getEnd())){
	// 	cout<<"cppp2"<<endl;
	// }
         
	return LocationIsInRange(s->getBeginLoc(), *case_value_range_);
}

bool StmtContext::IsInArraySubscriptRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *arraysubscript_range_);
}

bool StmtContext::IsInSwitchCaseRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *switchcase_range_);
}

bool StmtContext::IsInNonFloatingExprRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *non_floating_expr_range_);
}

bool StmtContext::IsInTypedefRange(Stmt *s)
{
	return LocationIsInRange(s->getBeginLoc(), *typedef_range_);
}

bool StmtContext::IsInCurrentlyParsedFunctionRange(clang::SourceLocation loc)
{
  return LocationIsInRange(loc, *currently_parsed_function_range_);
}

bool StmtContext::IsInLambdaRange(clang::SourceLocation loc)
{
  return LocationIsInRange(loc, *Lambda_expr_);
}

bool StmtContext::IsInDeclStmt(clang::SourceLocation loc)
{
  return LocationIsInRange(loc, *decl_stmt_);
}

bool StmtContext::IsInNonFloatingExprRange(clang::SourceLocation loc)
{
  return LocationIsInRange(loc, *non_floating_expr_range_);
}

bool StmtContext::IsInTypedefRange(clang::SourceLocation loc)
{
  return LocationIsInRange(loc, *typedef_range_);
}

bool StmtContext::IsInLoopRange(clang::SourceLocation loc)
{
  while (!loop_scope_list_->empty() && 
         !LocationIsInRange(loc, loop_scope_list_->back().second))
    loop_scope_list_->pop_back();

  return !loop_scope_list_->empty();
}

std::string StmtContext::getContainingFunction(clang::SourceLocation loc, clang::SourceManager& src_mgr)
{
  BeforeThanCompare<SourceLocation> isBefore(src_mgr);

  if (isBefore(loc, currently_parsed_function_range_->getEnd()) &&
      !isBefore(loc, currently_parsed_function_range_->getBegin()))
    return currently_parsed_function_name_;
  else
    return "MUSIC_global";
}
